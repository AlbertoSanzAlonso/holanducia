import logging
from typing import Any, Callable, Coroutine, Dict, List, Literal, Optional, TypedDict, Union

from langgraph.graph import END, START, StateGraph

from scrapers.agency.graphs.property_pipeline import run_property_pipeline
from scrapers.agency.scout import ScoutAgent
from scrapers.db_connector import DatabaseConnector

from scrapers.fb_utils import is_property_listing_text

logger = logging.getLogger(__name__)

FacebookPost = Dict[str, Any]


class FacebookPipelineState(TypedDict, total=False):
    group_url: str
    page_text: str
    dom_posts: List[Union[str, FacebookPost]]
    dom_urls: List[str]
    dom_images: List[str]
    posts: List[FacebookPost]
    extraction_method: Optional[str]
    diagnosis: Optional[Dict[str, Any]]
    candidates: List[FacebookPost]
    saved_count: int
    skipped_count: int
    stats: Dict[str, Any]
    limit: int
    error: Optional[str]
    ai_attempted: bool


PersistFn = Callable[[Dict[str, Any], str], Coroutine[Any, Any, bool]]
DedupCheckFn = Callable[[str], Coroutine[Any, Any, bool]]
MarkScrapedFn = Callable[[str], Coroutine[Any, Any, None]]


def _normalize_post(item: Any) -> Optional[FacebookPost]:
    if isinstance(item, dict):
        text = (item.get("text") or item.get("raw_text") or "").strip()
        if len(text) < 40:
            return None
        return {
            "text": text,
            "url": (item.get("url") or "").strip(),
            "images": item.get("images") or [],
        }
    text = str(item).strip()
    if len(text) < 40:
        return None
    return {"text": text, "url": "", "images": []}


def _post_text(post: FacebookPost) -> str:
    return (post.get("text") or "").strip()


def build_facebook_graph(
    connector: DatabaseConnector,
    persist_lead: PersistFn,
    is_already_scraped: DedupCheckFn,
    mark_as_scraped: MarkScrapedFn,
):
    scout = ScoutAgent()

    async def use_dom_posts(state: FacebookPipelineState) -> FacebookPipelineState:
        posts: List[FacebookPost] = []
        for raw in state.get("dom_posts", []):
            normalized = _normalize_post(raw)
            if normalized:
                posts.append(normalized)

        with_url = sum(1 for p in posts if p.get("url"))
        with_img = sum(1 for p in posts if p.get("images"))
        method = "dom" if posts else None
        logger.info(
            "LangGraph [use_dom_posts]: %s posts (%s con enlace, %s con foto)",
            len(posts),
            with_url,
            with_img,
        )
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
        raw_posts = await scout.extract_posts_from_text(state.get("page_text", ""), "Facebook")
        posts = []
        dom_urls = state.get("dom_urls") or []
        dom_images = state.get("dom_images") or []
        imgs_per_post = max(1, len(dom_images) // max(len(raw_posts), 1)) if dom_images else 0
        for i, raw in enumerate(raw_posts):
            normalized = _normalize_post(raw)
            if not normalized:
                continue
            if not normalized.get("url") and i < len(dom_urls):
                normalized["url"] = dom_urls[i]
            if not normalized.get("images") and imgs_per_post > 0:
                start = i * imgs_per_post
                end = start + imgs_per_post
                normalized["images"] = dom_images[start:end]
            posts.append(normalized)

        with_url = sum(1 for p in posts if p.get("url"))
        with_img = sum(1 for p in posts if p.get("images"))
        total_imgs = sum(len(p.get("images") or []) for p in posts)
        logger.info(
            "LangGraph [ai_extract]: Scout extrajo %s posts vía IA (%s con enlace, %s con foto, %s imgs totales)",
            len(posts), with_url, with_img, total_imgs,
        )
        return {"posts": posts, "extraction_method": "ai", "ai_attempted": True}

    async def filter_candidates(state: FacebookPipelineState) -> FacebookPipelineState:
        posts = state.get("posts", [])
        candidates = [
            p for p in posts
            if is_property_listing_text(_post_text(p))
        ]

        logger.info(
            "LangGraph [filter]: %s candidatos inmobiliarios de %s posts",
            len(candidates),
            len(posts),
        )
        if not candidates and posts:
            for i, post in enumerate(posts[:2]):
                preview = _post_text(post)[:120].replace("\n", " ")
                logger.warning("Post sin keywords #%s: %s…", i + 1, preview)

        stats = dict(state.get("stats") or {})
        stats.update({"posts_total": len(posts), "keyword_candidates": len(candidates)})
        return {"candidates": candidates, "stats": stats}

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
            "stats": {**dict(state.get("stats") or {}), **dict(result.get("stats") or {})},
        }

    async def abort(state: FacebookPipelineState) -> FacebookPipelineState:
        diagnosis = state.get("diagnosis") or {}
        error = diagnosis.get("message") or "Scraping abortado por diagnóstico del Scout"
        logger.warning("LangGraph [abort]: %s", error)
        return {"error": error, "saved_count": 0}

    def route_after_dom(state: FacebookPipelineState) -> Literal["filter", "diagnose"]:
        # Siempre filtrar primero; si el DOM capturó basura de UI, el fallback IA entra tras filter.
        return "filter" if state.get("posts") else "diagnose"

    def route_after_diagnose(state: FacebookPipelineState) -> Literal["ai_extract", "abort"]:
        status = (state.get("diagnosis") or {}).get("status", "unknown")
        if status in ("login_required", "join_required", "blocked"):
            return "abort"
        return "ai_extract"

    def route_after_filter(
        state: FacebookPipelineState,
    ) -> Literal["process", "diagnose", "__end__"]:
        if state.get("candidates"):
            return "process"
        if not state.get("ai_attempted"):
            return "diagnose"
        return END

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
    graph.add_conditional_edges(
        "filter",
        route_after_filter,
        {"process": "process", "diagnose": "diagnose", END: END},
    )
    graph.add_edge("process", END)
    graph.add_edge("abort", END)

    return graph.compile()


async def run_facebook_pipeline(
    group_url: str,
    page_text: str,
    dom_posts: List[Union[str, FacebookPost]],
    dom_urls: Optional[List[str]] = None,
    dom_images: Optional[List[str]] = None,
    limit: int = 50,
    connector: DatabaseConnector = None,
    persist_lead: PersistFn = None,
    is_already_scraped: DedupCheckFn = None,
    mark_as_scraped: MarkScrapedFn = None,
) -> FacebookPipelineState:
    graph = build_facebook_graph(connector, persist_lead, is_already_scraped, mark_as_scraped)
    initial: FacebookPipelineState = {
        "group_url": group_url,
        "page_text": page_text,
        "dom_posts": dom_posts,
        "dom_urls": dom_urls or [],
        "dom_images": dom_images or [],
        "posts": [],
        "candidates": [],
        "saved_count": 0,
        "limit": limit,
        "ai_attempted": False,
    }
    return await graph.ainvoke(initial)
