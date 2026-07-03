import re
from typing import Any, Iterable, List


SKIP_SUBSTRINGS = (
    "logo",
    "icon",
    "avatar",
    "sprite",
    "placeholder",
    "1x1",
    "pixel",
    "cookie",
    "banner",
    ".svg",
    "facebook",
    "google",
    "didomi",
    "tracking",
    "analytics",
)

PREFERRED_SUBSTRINGS = (
    "pisos.com",
    "fotocasa",
    "habitaclia",
    "idealista",
    "img.",
    "images.",
    "cloudfront",
    "cdn",
)


def extract_image_urls(
    *,
    html: str = "",
    markdown: str = "",
    media_images: Iterable[Any] = None,
) -> List[str]:
    urls: List[str] = []

    for item in media_images or []:
        if isinstance(item, str):
            urls.append(item)
        elif isinstance(item, dict):
            candidate = item.get("src") or item.get("url") or item.get("href")
            if candidate:
                urls.append(str(candidate))

    for text in (markdown or "", html or ""):
        urls.extend(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text))
        urls.extend(
            re.findall(
                r'(?:src|data-src|href)=["\']([^"\']+\.(?:jpg|jpeg|webp|png)(?:\?[^"\']*)?)["\']',
                text,
                re.I,
            )
        )
        urls.extend(
            re.findall(
                r"https?://[^\s\"'<>]+\.(?:jpg|jpeg|webp|png)(?:\?[^\s\"'<>]*)?",
                text,
                re.I,
            )
        )

    seen: set[str] = set()
    clean: List[str] = []
    for url in urls:
        url = url.strip().split(" ")[0]
        if not url.startswith("http"):
            continue
        lower = url.lower()
        if any(token in lower for token in SKIP_SUBSTRINGS):
            continue
        if url in seen:
            continue
        seen.add(url)
        clean.append(url)

    clean.sort(key=_image_priority, reverse=True)
    return clean


def _image_priority(url: str) -> int:
    lower = url.lower()
    score = 0
    if any(token in lower for token in PREFERRED_SUBSTRINGS):
        score += 2
    if any(size in lower for size in ("1200", "1000", "800", "large", "xl")):
        score += 1
    if any(size in lower for size in ("thumb", "small", "mini", "50x", "100x")):
        score -= 1
    return score


def assign_images_to_leads(leads: List[dict], page_images: List[str], max_per_lead: int = 3) -> None:
    pool = list(page_images)
    for lead in leads:
        existing = lead.get("images") or []
        if existing:
            lead["images"] = existing[:max_per_lead]
            continue
        assigned: List[str] = []
        while pool and len(assigned) < max_per_lead:
            assigned.append(pool.pop(0))
        if assigned:
            lead["images"] = assigned


def is_portal_index_url(url: str) -> bool:
    lower = url.lower().rstrip("/")
    if lower.endswith(("/l", "/listado", "/listado.htm")):
        return True
    if re.search(r"/venta/pisos-[^/]+$", lower):
        return True
    if re.search(r"/comprar/viviendas/[^/]+/todas-las-zonas", lower):
        return True
    if re.search(r"/comprar-vivienda-en-[^/]+$", lower):
        return True
    return False
