"""Descarga imágenes de Facebook y las aloja en el VPS para persistencia."""
import hashlib
import logging
import os
import re
from pathlib import Path
from typing import List

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


async def download_facebook_images(image_urls: List[str], lead_key: str) -> List[str]:
    """Descarga fotos del CDN de FB y devuelve URLs públicas /api/media/properties/..."""
    if not image_urls:
        return []

    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    prefix = _safe_key(lead_key)
    hosted: List[str] = []

    async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
        for idx, url in enumerate(image_urls[:5]):
            if not url or not any(token in url.lower() for token in ("scontent", "fbcdn", "facebook")):
                continue
            try:
                response = await client.get(url, headers=FB_HEADERS)
                if response.status_code != 200:
                    logger.debug("Imagen FB HTTP %s: %s", response.status_code, url[:80])
                    continue
                if len(response.content) < 3000:
                    continue

                ext = _extension(response.headers.get("content-type", ""), url)
                filename = f"{prefix}_{idx}.{ext}"
                path = MEDIA_ROOT / filename
                path.write_bytes(response.content)
                hosted.append(f"/api/media/properties/{filename}")
                logger.info("Imagen FB guardada: %s (%s KB)", filename, len(response.content) // 1024)
            except Exception as e:
                logger.warning("No se pudo descargar imagen FB: %s — %s", url[:60], e)

    return hosted
