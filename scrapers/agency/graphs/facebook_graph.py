import logging
from typing import Any, Callable, Coroutine, Dict, List, Literal, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from scrapers.agency.graphs.property_pipeline import run_property_pipeline
from scrapers.agency.scout import ScoutAgent
from scrapers.db_connector import DatabaseConnector

logger = logging.getLogger(__name__)

REAL_ESTATE_KEYWORDS = [
    "piso", "casa", "vivienda", "alquiler", "vendo", "venta", "chalet", "inmueble",
    "hab", "dorm", "baño", "estudio", "loft", "duplex", "finca", "apartamento",
    "€", "euro", "precio", "m2", "particular", "inmobiliaria", "comunidad",
]


class FacebookPipelineState(TypedDict, total=False):
    group_url: str
    page_text: str
    dom_posts: List[str]
    posts: List[str]
    extraction_method: Optional[str]
    diagnosis: Optional[Dict[str, Any]]
    candidates: List[str]
    saved_count: int
    skipped_count: int
    stats: Dict[str, Any]
    limit: int
    error: Optional[str]


PersistFn = Callable[[Dict[str, Any], str], Coroutine[Any, Any, bool]]
DedupCheckFn = Callable[[str], Coroutine[Any, Any, bool]]
MarkScrapedFn = Callable[[str], Coroutine[Any, Any, None]]


def build_facebook_graph(
    connector: DatabaseConnector,
    persist_lead: PersistFn,
    is_already_scraped: DedupCheckFn,
    mark_as_scraped: MarkScrapedFn,
):
    scout = ScoutAgent()

    async def use_dom_posts(state: FacebookPipelineState) -> FacebookPipelineState:
        posts = [p.strip() for p in state.get("dom_posts", []) if len(p.strip()) > 50]
        method = "dom" if posts else None
        logger.info("LangGraph [use_dom_posts]: %s fragmentos del DOM", len(posts))
        return {"posts": posts, "extraction_method": method}

    async def diagnose_page(state: FacebookPipelineState) -> FacebookPipelineState:
        diagnosis = await scout.diagnose_page(state.get("page_text", ""), state["group_url"])
        logger.info(
            "LangGraph [diagnose]: status=%s — %s",
            diagnosis.get("status"),
            diagnosis.get("message"),
        )
        return {"diagnosis": diagnosis}

    async def ai_extract(state: FacebookPipelineState) -> FacebookPipelineState:
        posts = await scout.extract_posts_from_text(state.get("page_text", ""), "Facebook")
        logger.info("LangGraph [ai_extract]: Scout extrajo %s posts vía IA", len(posts))
        return {"posts": posts, "extraction_method": "ai"}

    async def filter_candidates(state: FacebookPipelineState) -> FacebookPipelineState:
        posts = state.get("posts", [])
        candidates = [p for p in posts if any(k in p.lower() for k in REAL_ESTATE_KEYWORDS)]
        logger.info(
            "LangGraph [filter]: %s candidatos inmobiliarios de %s posts",
            len(candidates),
            len(posts),
        )
        return {"candidates": candidates}

    async def process_pipeline(state: FacebookPipelineState) -> FacebookPipelineState:
        result = await run_property_pipeline(
            source="Facebook",
            base_url=state["group_url"],
            raw_candidates=state.get("candidates", []),
            limit=state.get("limit", 50),
            connector=connector,
            persist_lead=persist_lead,
            is_already_scraped=is_already_scraped,
            mark_as_scraped=mark_as_scraped,
        )
        return {
            "saved_count": result.get("saved_count", 0),
            "skipped_count": result.get("skipped_count", 0),
            "stats": result.get("stats", {}),
        }

    async def abort(state: FacebookPipelineState) -> FacebookPipelineState:
        diagnosis = state.get("diagnosis") or {}
        error = diagnosis.get("message") or "Scraping abortado por diagnóstico del Scout"
        logger.warning("LangGraph [abort]: %s", error)
        return {"error": error, "saved_count": 0}

    def route_after_dom(state: FacebookPipelineState) -> Literal["filter", "diagnose"]:
        return "filter" if state.get("posts") else "diagnose"

    def route_after_diagnose(state: FacebookPipelineState) -> Literal["ai_extract", "abort"]:
        status = (state.get("diagnosis") or {}).get("status", "unknown")
        if status in ("login_required", "join_required", "blocked"):
            return "abort"
        return "ai_extract"

    def route_after_filter(state: FacebookPipelineState) -> Literal["process", "__end__"]:
        return "process" if state.get("candidates") else END

    graph = StateGraph(FacebookPipelineState)
    graph.add_node("use_dom_posts", use_dom_posts)
    graph.add_node("diagnose", diagnose_page)
    graph.add_node("ai_extract", ai_extract)
    graph.add_node("filter", filter_candidates)
    graph.add_node("process", process_pipeline)
    graph.add_node("abort", abort)

    graph.add_edge(START, "use_dom_posts")
    graph.add_conditional_edges("use_dom_posts", route_after_dom, {"filter": "filter", "diagnose": "diagnose"})
    graph.add_conditional_edges("diagnose", route_after_diagnose, {"ai_extract": "ai_extract", "abort": "abort"})
    graph.add_edge("ai_extract", "filter")
    graph.add_conditional_edges("filter", route_after_filter, {"process": "process", END: END})
    graph.add_edge("process", END)
    graph.add_edge("abort", END)

    return graph.compile()


async def run_facebook_pipeline(
    group_url: str,
    page_text: str,
    dom_posts: List[str],
    limit: int,
    connector: DatabaseConnector,
    persist_lead: PersistFn,
    is_already_scraped: DedupCheckFn,
    mark_as_scraped: MarkScrapedFn,
) -> FacebookPipelineState:
    graph = build_facebook_graph(connector, persist_lead, is_already_scraped, mark_as_scraped)
    initial: FacebookPipelineState = {
        "group_url": group_url,
        "page_text": page_text,
        "dom_posts": dom_posts,
        "posts": [],
        "candidates": [],
        "saved_count": 0,
        "limit": limit,
    }
    return await graph.ainvoke(initial)
