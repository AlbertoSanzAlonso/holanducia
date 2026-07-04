"""Descarga y aloja imágenes de anuncios (Facebook, portales) en el VPS."""
import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Any, List, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "/app/media/properties"))
MAX_PROPERTY_IMAGES = int(os.getenv("MAX_PROPERTY_IMAGES", "30"))
MIN_IMAGE_BYTES = int(os.getenv("MIN_PROPERTY_IMAGE_BYTES", "2000"))

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}

FB_HEADERS = {
    **DEFAULT_HEADERS,
    "Referer": "https://www.facebook.com/",
}


def _safe_key(key: str) -> str:
    digest = hashlib.md5(key.encode()).hexdigest()[:12]
    clean = re.sub(r"[^\w-]", "_", key)[:20]
    return f"{clean}_{digest}" if clean else digest


def _extension(content_type: str, url: str) -> str:
    ct = (content_type or "").lower()
    if "png" in ct:
        return "png"
    if "webp" in ct:
        return "webp"
    if "gif" in ct:
        return "gif"
    if url.lower().endswith(".png"):
        return "png"
    if url.lower().endswith(".webp"):
        return "webp"
    return "jpg"


def is_hosted_url(url: str) -> bool:
    u = (url or "").strip()
    return u.startswith("/api/media/properties/")


def _is_facebook_cdn(url: str) -> bool:
    lower = (url or "").lower()
    return any(token in lower for token in ("scontent", "fbcdn", "facebook"))


def _portal_headers(referer: Optional[str]) -> dict:
    headers = dict(DEFAULT_HEADERS)
    if referer and referer.startswith("http"):
        headers["Referer"] = referer
    return headers


def _save_bytes(content: bytes, lead_key: str, idx: int, content_type: str, url: str) -> Optional[str]:
    if len(content) < MIN_IMAGE_BYTES:
        return None
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    prefix = _safe_key(lead_key)
    ext = _extension(content_type, url)
    filename = f"{prefix}_{idx}.{ext}"
    path = MEDIA_ROOT / filename
    if path.exists() and path.stat().st_size >= MIN_IMAGE_BYTES:
        return f"/api/media/properties/{filename}"
    path.write_bytes(content)
    logger.info("Imagen guardada: %s (%s KB)", filename, len(content) // 1024)
    return f"/api/media/properties/{filename}"


async def _download_with_page(
    page: Any,
    image_urls: List[str],
    lead_key: str,
    start_idx: int,
) -> List[str]:
    hosted: List[str] = []
    for offset, url in enumerate(image_urls):
        if not url:
            continue
        try:
            response = await page.request.get(url)
            if response.status != 200:
                continue
            body = await response.body()
            saved = _save_bytes(body, lead_key, start_idx + offset, response.headers.get("content-type", ""), url)
            if saved:
                hosted.append(saved)
        except Exception as e:
            logger.warning("Imagen (page) falló %s: %s", url[:60], e)
    return hosted


async def _download_http(
    image_urls: List[str],
    lead_key: str,
    start_idx: int,
    headers: dict,
) -> List[str]:
    hosted: List[str] = []
    async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
        for offset, url in enumerate(image_urls):
            if not url:
                continue
            try:
                response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    logger.debug("Imagen HTTP %s: %s", response.status_code, url[:80])
                    continue
                saved = _save_bytes(
                    response.content,
                    lead_key,
                    start_idx + offset,
                    response.headers.get("content-type", ""),
                    url,
                )
                if saved:
                    hosted.append(saved)
            except Exception as e:
                logger.warning("Imagen HTTP falló %s: %s", url[:60], e)
    return hosted


async def host_property_images(
    image_urls: List[str],
    lead_key: str,
    *,
    referer: Optional[str] = None,
    page: Any = None,
) -> List[str]:
    """Descarga hasta MAX_PROPERTY_IMAGES; conserva las ya alojadas en /api/media/."""
    if not image_urls:
        return []

    seen: set[str] = set()
    hosted: List[str] = []
    to_download: List[str] = []

    for url in image_urls:
        url = (url or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        if is_hosted_url(url):
            hosted.append(url)
        elif url.startswith("http"):
            to_download.append(url)
        if len(hosted) + len(to_download) >= MAX_PROPERTY_IMAGES:
            break

    remaining = MAX_PROPERTY_IMAGES - len(hosted)
    to_download = to_download[:remaining]

    fb_urls = [u for u in to_download if _is_facebook_cdn(u)]
    portal_urls = [u for u in to_download if not _is_facebook_cdn(u)]

    if fb_urls:
        if page is not None:
            hosted.extend(await _download_with_page(page, fb_urls, lead_key, len(hosted)))
        else:
            hosted.extend(await _download_http(fb_urls, lead_key, len(hosted), FB_HEADERS))

    if portal_urls and len(hosted) < MAX_PROPERTY_IMAGES:
        portal_urls = portal_urls[: MAX_PROPERTY_IMAGES - len(hosted)]
        hosted.extend(await _download_http(portal_urls, lead_key, len(hosted), _portal_headers(referer)))

    if hosted:
        return hosted[:MAX_PROPERTY_IMAGES]

    # Último recurso: URLs remotas (pueden caducar)
    remote = [u for u in image_urls if u.startswith("http")]
    return remote[:MAX_PROPERTY_IMAGES]


async def host_facebook_images(
    image_urls: List[str],
    lead_key: str,
    *,
    page: Any = None,
) -> List[str]:
    return await host_property_images(image_urls, lead_key, referer="https://www.facebook.com/", page=page)
