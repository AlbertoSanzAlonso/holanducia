"""Descarga imágenes de Facebook y las aloja en el VPS para persistencia."""
import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Any, List, Optional

import httpx

logger = logging.getLogger(__name__)

MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "/app/media/properties"))
FB_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.facebook.com/",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
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


def _is_facebook_cdn(url: str) -> bool:
    lower = (url or "").lower()
    return any(token in lower for token in ("scontent", "fbcdn", "facebook"))


def _save_bytes(content: bytes, lead_key: str, idx: int, content_type: str, url: str) -> Optional[str]:
    if len(content) < 2000:
        return None
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    prefix = _safe_key(lead_key)
    ext = _extension(content_type, url)
    filename = f"{prefix}_{idx}.{ext}"
    path = MEDIA_ROOT / filename
    path.write_bytes(content)
    public_url = f"/api/media/properties/{filename}"
    logger.info("Imagen FB guardada: %s (%s KB)", filename, len(content) // 1024)
    return public_url


async def download_facebook_images_with_page(page: Any, image_urls: List[str], lead_key: str) -> List[str]:
    """Descarga con la sesión activa de Playwright (cookies de FB)."""
    if not image_urls or page is None:
        return []

    hosted: List[str] = []
    for idx, url in enumerate(image_urls[:5]):
        if not url or not _is_facebook_cdn(url):
            continue
        try:
            response = await page.request.get(url)
            if response.status != 200:
                logger.debug("Imagen FB (page) HTTP %s: %s", response.status, url[:80])
                continue
            body = await response.body()
            saved = _save_bytes(body, lead_key, idx, response.headers.get("content-type", ""), url)
            if saved:
                hosted.append(saved)
        except Exception as e:
            logger.warning("No se pudo descargar imagen FB (page): %s — %s", url[:60], e)

    return hosted


async def download_facebook_images(image_urls: List[str], lead_key: str) -> List[str]:
    """Fallback HTTP sin cookies (suele fallar en CDN de FB)."""
    if not image_urls:
        return []

    hosted: List[str] = []
    async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
        for idx, url in enumerate(image_urls[:5]):
            if not url or not _is_facebook_cdn(url):
                continue
            try:
                response = await client.get(url, headers=FB_HEADERS)
                if response.status_code != 200:
                    logger.debug("Imagen FB HTTP %s: %s", response.status_code, url[:80])
                    continue
                saved = _save_bytes(
                    response.content,
                    lead_key,
                    idx,
                    response.headers.get("content-type", ""),
                    url,
                )
                if saved:
                    hosted.append(saved)
            except Exception as e:
                logger.warning("No se pudo descargar imagen FB: %s — %s", url[:60], e)

    return hosted


async def host_facebook_images(
    image_urls: List[str],
    lead_key: str,
    *,
    page: Any = None,
) -> List[str]:
    """Intenta Playwright primero; conserva URLs CDN como último recurso."""
    if not image_urls:
        return []

    hosted: List[str] = []
    if page is not None:
        hosted = await download_facebook_images_with_page(page, image_urls, lead_key)

    if not hosted:
        hosted = await download_facebook_images(image_urls, lead_key)

    if hosted:
        return hosted

    # Mejor enlace CDN que nada (puede caducar, pero visible a veces)
    return [u for u in image_urls[:5] if u and _is_facebook_cdn(u)]
