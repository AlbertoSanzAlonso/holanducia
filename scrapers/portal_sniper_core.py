"""Lógica compartida de extracción profunda de fichas de portales."""
import asyncio
import logging
import os
from typing import Any, Awaitable, Callable, Dict, List, Optional

from scrapers.portal_detail_parser import is_card_snippet, parse_portal_detail
from scrapers.portal_utils import extract_listing_urls, is_listing_detail_url, portal_host
from scrapers.image_utils import is_portal_index_url

logger = logging.getLogger(__name__)

MAX_PER_INDEX = int(os.getenv("PORTAL_DETAILS_PER_INDEX", "40"))
DETAIL_CONCURRENCY = int(os.getenv("PORTAL_DETAIL_CONCURRENCY", "4"))


def is_incomplete_portal_record(prop: Optional[Dict[str, Any]]) -> bool:
    if not prop:
        return False
    title = prop.get("title") or ""
    description = prop.get("description") or ""
    if is_card_snippet(title, description):
        return True
    price = float(prop.get("price") or 0)
    size_m2 = prop.get("size_m2")
    rooms = prop.get("rooms")
    if price > 0 and size_m2 in (None, 0) and rooms in (None, 0):
        return True
    if is_listing_detail_url(prop.get("url") or "") and len(description.strip()) < 120:
        return True
    return False


def collect_detail_urls(urls: List[str]) -> List[str]:
    """Separa URLs índice (para descubrir) de fichas directas."""
    index_urls: List[str] = []
    detail_urls: List[str] = []

    for url in urls:
        if is_portal_index_url(url):
            index_urls.append(url)
        elif is_listing_detail_url(url):
            detail_urls.append(url)
        else:
            detail_urls.append(url)

    return list(dict.fromkeys(index_urls)), list(dict.fromkeys(detail_urls))


async def discover_from_index(
    index_url: str,
    fetch_page: Callable[[str], Awaitable[Optional[Dict[str, Any]]]],
) -> List[str]:
    data = await fetch_page(index_url)
    if not data:
        return []
    listing_urls = extract_listing_urls(
        data.get("html") or "",
        data.get("markdown") or "",
        index_url,
    )
    logger.info("Índice %s → %s fichas detectadas", index_url[:60], len(listing_urls))
    return listing_urls[:MAX_PER_INDEX]


async def build_detail_url_queue(
    urls: List[str],
    fetch_page: Callable[[str], Awaitable[Optional[Dict[str, Any]]]],
    limit: int,
) -> List[str]:
    index_urls, detail_urls = collect_detail_urls(urls)

    for index_url in index_urls:
        if len(detail_urls) >= limit:
            break
        discovered = await discover_from_index(index_url, fetch_page)
        for u in discovered:
            if u not in detail_urls:
                detail_urls.append(u)
            if len(detail_urls) >= limit:
                break

    return detail_urls[:limit]


async def extract_portal_lead(
    analyst,
    *,
    url: str,
    markdown: str,
    html: str = "",
    images: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    source_name = portal_host(url) or url.split("//")[-1].split("/")[0].replace("www.", "")

    pre_parsed = parse_portal_detail(url, markdown, html=html, images=images or [])
    pre_parsed.pop("_parse_meta", None)

    if is_card_snippet(pre_parsed.get("title"), pre_parsed.get("description")):
        logger.warning("Tarjeta/listado detectado en %s — IA profunda", url[:70])
        pre_parsed = {"images": (images or [])[:8], "url": url}

    lead = await analyst.parse_portal_detail(
        markdown,
        source_name,
        url=url,
        pre_parsed=pre_parsed,
    )
    if not lead:
        return None

    lead["url"] = url.rstrip("/")
    lead["source"] = source_name
    if images and not lead.get("images"):
        lead["images"] = images[:8]
    return lead


async def scrape_detail_urls_parallel(
    detail_urls: List[str],
    *,
    fetch_page: Callable[[str], Awaitable[Optional[Dict[str, Any]]]],
    analyst,
    should_skip: Callable[[str], Awaitable[bool]],
) -> List[Dict[str, Any]]:
    sem = asyncio.Semaphore(DETAIL_CONCURRENCY)

    async def one(url: str) -> Optional[Dict[str, Any]]:
        if await should_skip(url):
            logger.info("⏭️ Omitiendo ficha (cache/ok): %s", url[:70])
            return None
        async with sem:
            data = await fetch_page(url)
            if not data:
                return None
            markdown = (data.get("markdown") or "").strip()
            if not markdown:
                return None
            return await extract_portal_lead(
                analyst,
                url=url,
                markdown=markdown,
                html=data.get("html") or "",
                images=data.get("images") or [],
            )

    results = await asyncio.gather(*[one(u) for u in detail_urls])
    return [lead for lead in results if lead]
