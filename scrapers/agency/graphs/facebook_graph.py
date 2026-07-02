import hashlib
import logging
from typing import Any, Callable, Coroutine, Dict, List, Literal, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from scrapers.agency.analyst import AnalystAgent
from scrapers.agency.scout import ScoutAgent

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
    leads: List[Dict[str, Any]]
    saved_count: int
    limit: int
    error: Optional[str]


PersistFn = Callable[[Dict[str, Any], str], Coroutine[Any, Any, bool]]
DedupCheckFn = Callable[[str], Coroutine[Any, Any, bool]]
MarkScrapedFn = Callable[[str], Coroutine[Any, Any, None]]


def build_facebook_graph(
    persist_lead: PersistFn,
    is_already_scraped: DedupCheckFn,
    mark_as_scraped: MarkScrapedFn,
):
    scout = ScoutAgent()
    analyst = AnalystAgent()

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
        candidates = [
            p for p in posts
            if any(k in p.lower() for k in REAL_ESTATE_KEYWORDS)
        ]
        logger.info(
            "LangGraph [filter]: %s candidatos inmobiliarios de %s posts",
            len(candidates),
            len(posts),
        )
        return {"candidates": candidates}

    async def analyze_leads(state: FacebookPipelineState) -> FacebookPipelineState:
        leads: List[Dict[str, Any]] = []
        limit = state.get("limit", 50)

        for post_text in state.get("candidates", []):
            if len(leads) >= limit:
                break
            ai_data = await analyst.parse_raw_text(post_text, "Facebook")
            if ai_data:
                ai_data.pop("is_real_estate", None)
                leads.append(ai_data)

        logger.info("LangGraph [analyze]: %s leads estructurados", len(leads))
        return {"leads": leads}

    async def persist_leads(state: FacebookPipelineState) -> FacebookPipelineState:
        saved = 0
        group_url = state["group_url"]

        for ai_data in state.get("leads", []):
            if saved >= state.get("limit", 50):
                break

            f_hash = hashlib.md5(f"{ai_data['title']}{ai_data['price']}".encode()).hexdigest()[:12]
            if await is_already_scraped(f_hash):
                continue

            ai_data["external_id"] = f_hash
            ai_data["url"] = f"{group_url}?post_id={f_hash}"
            if await persist_lead(ai_data, group_url):
                saved += 1
                await mark_as_scraped(f_hash)
                logger.info("LangGraph [persist]: lead guardado — %s", ai_data["title"])

        return {"saved_count": saved}

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

    def route_after_filter(state: FacebookPipelineState) -> Literal["analyze", "__end__"]:
        return "analyze" if state.get("candidates") else END

    graph = StateGraph(FacebookPipelineState)
    graph.add_node("use_dom_posts", use_dom_posts)
    graph.add_node("diagnose", diagnose_page)
    graph.add_node("ai_extract", ai_extract)
    graph.add_node("filter", filter_candidates)
    graph.add_node("analyze", analyze_leads)
    graph.add_node("persist", persist_leads)
    graph.add_node("abort", abort)

    graph.add_edge(START, "use_dom_posts")
    graph.add_conditional_edges("use_dom_posts", route_after_dom, {"filter": "filter", "diagnose": "diagnose"})
    graph.add_conditional_edges("diagnose", route_after_diagnose, {"ai_extract": "ai_extract", "abort": "abort"})
    graph.add_edge("ai_extract", "filter")
    graph.add_conditional_edges("filter", route_after_filter, {"analyze": "analyze", END: END})
    graph.add_edge("analyze", "persist")
    graph.add_edge("persist", END)
    graph.add_edge("abort", END)

    return graph.compile()


async def run_facebook_pipeline(
    group_url: str,
    page_text: str,
    dom_posts: List[str],
    limit: int,
    persist_lead: PersistFn,
    is_already_scraped: DedupCheckFn,
    mark_as_scraped: MarkScrapedFn,
) -> FacebookPipelineState:
    graph = build_facebook_graph(persist_lead, is_already_scraped, mark_as_scraped)
    initial: FacebookPipelineState = {
        "group_url": group_url,
        "page_text": page_text,
        "dom_posts": dom_posts,
        "posts": [],
        "candidates": [],
        "leads": [],
        "saved_count": 0,
        "limit": limit,
    }
    return await graph.ainvoke(initial)
