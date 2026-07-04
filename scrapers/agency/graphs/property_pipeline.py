import logging
from typing import Any, Callable, Coroutine, Dict, List

from langgraph.graph import END, START, StateGraph

from scrapers.agency.analyst import AnalystAgent
from scrapers.agency.curator import CuratorAgent
from scrapers.agency.fb_classifier import FacebookClassifierAgent
from scrapers.agency.persist import persist_supervised_leads
from scrapers.agency.supervisor import SupervisorAgent
from scrapers.fb_utils import enrich_lead_from_raw, is_quality_facebook_lead, is_property_listing_text
from scrapers.portal_utils import normalize_facebook_post_url
from scrapers.agency.types import PropertyPipelineState
from scrapers.db_connector import DatabaseConnector

logger = logging.getLogger(__name__)

PersistFn = Callable[[Dict[str, Any], str], Coroutine[Any, Any, bool]]
DedupCheckFn = Callable[[str], Coroutine[Any, Any, bool]]
MarkScrapedFn = Callable[[str], Coroutine[Any, Any, None]]


def build_property_pipeline(
    connector: DatabaseConnector,
    persist_lead: PersistFn,
    is_already_scraped: DedupCheckFn,
    mark_as_scraped: MarkScrapedFn,
):
    curator = CuratorAgent(connector, is_already_scraped)
    analyst = AnalystAgent()
    supervisor = SupervisorAgent()
    fb_classifier = FacebookClassifierAgent()

    async def curate_candidates(state: PropertyPipelineState) -> PropertyPipelineState:
        source = state.get("source", "Unknown")
        base_url = state["base_url"]
        raw_candidates = state.get("raw_candidates", [])

        approved, skipped = await curator.curate_batch(
            raw_candidates,
            source=source,
            base_url=base_url,
        )

        stats = dict(state.get("stats") or {})
        stats.update({"raw_in": len(raw_candidates), "curated_out": len(approved), "duplicates": skipped})

        return {"approved": approved, "skipped_count": skipped, "stats": stats}

    async def analyze_approved(state: PropertyPipelineState) -> PropertyPipelineState:
        leads: List[Dict[str, Any]] = []
        raw_text_map: Dict[str, str] = {}
        limit = state.get("limit", 50)
        source = state.get("source", "Unknown")
        rejected_non_real_estate = 0
        rejected_low_quality = 0
        rejected_classifier = 0

        for item in state.get("approved", []):
            if len(leads) >= limit:
                break
            raw_text = item["raw_text"]
            metadata = item.get("metadata") or {}
            images = metadata.get("images") or []
            has_images = len(images) > 0

            if source == "Facebook":
                if not is_property_listing_text(raw_text, has_images=has_images):
                    rejected_classifier += 1
                    continue
                classification = await fb_classifier.classify(raw_text)
                if not fb_classifier.passes(classification):
                    rejected_classifier += 1
                    logger.info(
                        "FB Classifier rechazado (%.0f%%): %s — %s",
                        classification["confidence"] * 100,
                        classification["reason"],
                        raw_text[:70],
                    )
                    continue

            ai_data = await analyst.parse_raw_text(
                raw_text,
                source,
                prequalified=(source == "Facebook"),
            )
            if not ai_data:
                rejected_non_real_estate += 1
                continue
            ai_data.pop("is_real_estate", None)
            dedup_key = item.get("dedup_key")
            ai_data["_raw_dedup_key"] = dedup_key
            raw_text_map[dedup_key or ""] = raw_text

            meta = item.get("metadata") or {}
            post_url = normalize_facebook_post_url(item.get("url") or "") or (item.get("url") or meta.get("url") or "")
            if post_url:
                ai_data["url"] = post_url.strip()
            dom_images = meta.get("images") or []
            if dom_images:
                ai_data["images"] = dom_images
            if source == "Facebook" and ai_data.get("is_individual") is None:
                ai_data["is_individual"] = True

            if source == "Facebook":
                ai_data = enrich_lead_from_raw(ai_data, raw_text)
                if not is_quality_facebook_lead(ai_data, raw_text):
                    rejected_low_quality += 1
                    logger.info(
                        "PropertyPipeline [analyze]: pre-filtro calidad — %s",
                        (ai_data.get("title") or raw_text[:60]),
                    )
                    continue

            leads.append(ai_data)

        stats = dict(state.get("stats") or {})
        stats["analyzed"] = len(leads)
        stats["rejected_non_real_estate"] = rejected_non_real_estate
        stats["rejected_low_quality"] = rejected_low_quality
        stats["rejected_classifier"] = rejected_classifier
        logger.info(
            "PropertyPipeline [analyze]: %s leads, %s classifier, %s no-inmobiliario, %s baja calidad",
            len(leads),
            rejected_classifier,
            rejected_non_real_estate,
            rejected_low_quality,
        )
        return {"leads": leads, "stats": stats, "raw_text_map": raw_text_map}

    async def persist_leads(state: PropertyPipelineState) -> PropertyPipelineState:
        saved, skipped, persist_stats = await persist_supervised_leads(
            state.get("leads", []),
            source=state.get("source", "Unknown"),
            base_url=state["base_url"],
            limit=state.get("limit", 50),
            connector=connector,
            curator=curator,
            supervisor=supervisor,
            persist_lead=persist_lead,
            mark_as_scraped=mark_as_scraped,
            raw_text_by_key=state.get("raw_text_map") or {},
            skipped=state.get("skipped_count", 0),
        )

        stats = dict(state.get("stats") or {})
        stats.update(persist_stats)
        return {"saved_count": saved, "skipped_count": skipped, "stats": stats}

    def route_after_curate(state: PropertyPipelineState):
        return "analyze" if state.get("approved") else END

    def route_after_analyze(state: PropertyPipelineState):
        return "persist" if state.get("leads") else END

    graph = StateGraph(PropertyPipelineState)
    graph.add_node("curate", curate_candidates)
    graph.add_node("analyze", analyze_approved)
    graph.add_node("persist", persist_leads)

    graph.add_edge(START, "curate")
    graph.add_conditional_edges("curate", route_after_curate, {"analyze": "analyze", END: END})
    graph.add_conditional_edges("analyze", route_after_analyze, {"persist": "persist", END: END})
    graph.add_edge("persist", END)

    return graph.compile()


async def run_property_pipeline(
    *,
    source: str,
    base_url: str,
    raw_candidates: List[Any],
    limit: int,
    connector: DatabaseConnector,
    persist_lead: PersistFn,
    is_already_scraped: DedupCheckFn,
    mark_as_scraped: MarkScrapedFn,
) -> PropertyPipelineState:
    graph = build_property_pipeline(connector, persist_lead, is_already_scraped, mark_as_scraped)
    initial: PropertyPipelineState = {
        "source": source,
        "base_url": base_url,
        "raw_candidates": raw_candidates,
        "approved": [],
        "leads": [],
        "saved_count": 0,
        "skipped_count": 0,
        "limit": limit,
        "stats": {},
        "raw_text_map": {},
    }
    return await graph.ainvoke(initial)


async def run_structured_leads_pipeline(
    *,
    source: str,
    base_url: str,
    leads: List[Dict[str, Any]],
    limit: int,
    connector: DatabaseConnector,
    persist_lead: PersistFn,
    is_already_scraped: DedupCheckFn,
    mark_as_scraped: MarkScrapedFn,
) -> PropertyPipelineState:
    """Portales: leads estructurados → Supervisor → Postgres + vector."""
    curator = CuratorAgent(connector, is_already_scraped)
    supervisor = SupervisorAgent()

    saved, skipped, persist_stats = await persist_supervised_leads(
        leads,
        source=source,
        base_url=base_url,
        limit=limit,
        connector=connector,
        curator=curator,
        supervisor=supervisor,
        persist_lead=persist_lead,
        mark_as_scraped=mark_as_scraped,
    )

    stats: Dict[str, Any] = {
        "raw_in": len(leads),
        "curated_out": saved,
        "analyzed": len(leads),
        **persist_stats,
    }
    logger.info(
        "StructuredPipeline [%s]: %s guardados, %s rechazados supervisor, %s duplicados",
        source,
        saved,
        persist_stats.get("rejected_supervisor", 0),
        skipped,
    )
    return {
        "source": source,
        "base_url": base_url,
        "saved_count": saved,
        "skipped_count": skipped,
        "stats": stats,
    }
