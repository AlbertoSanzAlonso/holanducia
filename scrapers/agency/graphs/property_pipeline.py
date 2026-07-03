import logging
from typing import Any, Callable, Coroutine, Dict, List

from langgraph.graph import END, START, StateGraph

from scrapers.agency.analyst import AnalystAgent
from scrapers.agency.curator import CuratorAgent, make_lead_dedup_key
from scrapers.portal_utils import resolve_lead_identity
from scrapers.agency.types import CurateAction, PropertyPipelineState, RawLead
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
        limit = state.get("limit", 50)
        source = state.get("source", "Unknown")
        rejected_non_real_estate = 0

        for item in state.get("approved", []):
            if len(leads) >= limit:
                break
            ai_data = await analyst.parse_raw_text(
                item["raw_text"],
                source,
                prequalified=(source == "Facebook"),
            )
            if not ai_data:
                rejected_non_real_estate += 1
                continue
            ai_data.pop("is_real_estate", None)
            ai_data["_raw_dedup_key"] = item.get("dedup_key")
            leads.append(ai_data)

        stats = dict(state.get("stats") or {})
        stats["analyzed"] = len(leads)
        stats["rejected_non_real_estate"] = rejected_non_real_estate
        logger.info(
            "PropertyPipeline [analyze]: %s leads estructurados, %s descartados (no inmobiliario)",
            len(leads),
            rejected_non_real_estate,
        )
        return {"leads": leads, "stats": stats}

    async def persist_leads(state: PropertyPipelineState) -> PropertyPipelineState:
        saved = 0
        skipped = state.get("skipped_count", 0)
        base_url = state["base_url"]
        limit = state.get("limit", 50)

        for ai_data in state.get("leads", []):
            if saved >= limit:
                break

            dedup_key = make_lead_dedup_key(ai_data.get("title", ""), ai_data.get("price", 0))
            url, external_id = resolve_lead_identity(ai_data, base_url)
            ai_data["external_id"] = external_id
            ai_data["url"] = url

            decision = await curator.evaluate_lead(ai_data, url=url, dedup_key=dedup_key)
            if decision["action"] != CurateAction.NEW.value:
                skipped += 1
                logger.debug("Curator descartó lead (%s): %s", decision["reason"], url)
                continue

            if await persist_lead(ai_data, base_url):
                saved += 1
                await mark_as_scraped(url)
                raw_key = ai_data.pop("_raw_dedup_key", None)
                if raw_key:
                    await mark_as_scraped(raw_key)
                logger.info("PropertyPipeline [persist]: %s", ai_data.get("title"))

        stats = dict(state.get("stats") or {})
        stats["saved"] = saved
        stats["duplicates"] = skipped
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
    raw_candidates: List[str],
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
    """Para portales: leads ya extraídos por parse_bulk_text → Curator → Persist."""
    curator = CuratorAgent(connector, is_already_scraped)
    saved = 0
    skipped = 0

    for lead in leads:
        if saved >= limit:
            break

        dedup_key = make_lead_dedup_key(lead.get("title", ""), lead.get("price", 0))
        url, external_id = resolve_lead_identity(lead, base_url)
        lead = dict(lead)
        lead["external_id"] = external_id
        lead["url"] = url
        lead["source"] = source

        decision = await curator.evaluate_lead(lead, url=url, dedup_key=dedup_key)
        if decision["action"] != CurateAction.NEW.value:
            skipped += 1
            continue

        if await persist_lead(lead, base_url):
            saved += 1
            await mark_as_scraped(url)

    stats: Dict[str, Any] = {
        "raw_in": len(leads),
        "curated_out": saved,
        "duplicates": skipped,
        "analyzed": len(leads),
        "saved": saved,
    }
    logger.info(
        "StructuredPipeline [%s]: %s guardados, %s duplicados de %s",
        source,
        saved,
        skipped,
        len(leads),
    )
    return {
        "source": source,
        "base_url": base_url,
        "saved_count": saved,
        "skipped_count": skipped,
        "stats": stats,
    }
