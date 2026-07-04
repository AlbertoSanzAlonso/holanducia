import json
import os
import re
from typing import Any, Iterable, List
from urllib.parse import parse_qs, urlparse, urlunparse


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


MAX_PROPERTY_IMAGES = int(os.getenv("MAX_PROPERTY_IMAGES", "30"))

SIZE_QUERY_KEYS = frozenset(
    {"w", "h", "width", "height", "resize", "quality", "q", "crop", "fit", "auto"}
)


def _image_dedup_key(url: str) -> str:
    parsed = urlparse(url.split(" ")[0].strip())
    qs = parse_qs(parsed.query, keep_blank_values=False)
    filtered = {k: v for k, v in qs.items() if k.lower() not in SIZE_QUERY_KEYS}
    clean_query = "&".join(f"{k}={v[0]}" for k, v in sorted(filtered.items()))
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", clean_query, ""))


def _extract_json_ld_images(html: str) -> List[str]:
    urls: List[str] = []
    if not html:
        return urls
    for block in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.I | re.S,
    ):
        try:
            data = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            node = stack.pop()
            if not isinstance(node, dict):
                continue
            image = node.get("image")
            if isinstance(image, str) and image.startswith("http"):
                urls.append(image)
            elif isinstance(image, list):
                for item in image:
                    if isinstance(item, str) and item.startswith("http"):
                        urls.append(item)
                    elif isinstance(item, dict):
                        for key in ("url", "contentUrl", "@id"):
                            val = item.get(key)
                            if isinstance(val, str) and val.startswith("http"):
                                urls.append(val)
            for val in node.values():
                if isinstance(val, dict):
                    stack.append(val)
                elif isinstance(val, list):
                    stack.extend(v for v in val if isinstance(v, dict))
    return urls


def _extract_srcset_urls(text: str) -> List[str]:
    urls: List[str] = []
    for match in re.finditer(r'(?:srcset|data-srcset)=["\']([^"\']+)["\']', text, re.I):
        for part in match.group(1).split(","):
            candidate = part.strip().split()[0]
            if candidate.startswith("http"):
                urls.append(candidate)
    return urls


def extract_image_urls(
    *,
    html: str = "",
    markdown: str = "",
    media_images: Iterable[Any] = None,
    max_images: int | None = None,
) -> List[str]:
    limit = max_images if max_images is not None else MAX_PROPERTY_IMAGES
    urls: List[str] = []

    for item in media_images or []:
        if isinstance(item, str):
            urls.append(item)
        elif isinstance(item, dict):
            candidate = item.get("src") or item.get("url") or item.get("href")
            if candidate:
                urls.append(str(candidate))
            for key in ("srcset", "data-srcset"):
                raw = item.get(key)
                if raw:
                    urls.extend(_extract_srcset_urls(f'srcset="{raw}"'))

    urls.extend(_extract_json_ld_images(html or ""))

    for text in (markdown or "", html or ""):
        urls.extend(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text))
        urls.extend(_extract_srcset_urls(text))
        urls.extend(
            re.findall(
                r'(?:src|data-src|data-iesrc|data-lazy|href)=["\']([^"\']+\.(?:jpg|jpeg|webp|png|avif)(?:\?[^"\']*)?)["\']',
                text,
                re.I,
            )
        )
        urls.extend(
            re.findall(
                r"https?://[^\s\"'<>]+\.(?:jpg|jpeg|webp|png|avif)(?:\?[^\s\"'<>]*)?",
                text,
                re.I,
            )
        )
        urls.extend(re.findall(r'"contentUrl"\s*:\s*"(https?://[^"]+)"', text, re.I))

    seen_keys: set[str] = set()
    clean: List[str] = []
    for url in urls:
        url = url.strip().split(" ")[0]
        if not url.startswith("http"):
            continue
        lower = url.lower()
        if any(token in lower for token in SKIP_SUBSTRINGS):
            continue
        dedup = _image_dedup_key(url)
        if dedup in seen_keys:
            continue
        seen_keys.add(dedup)
        clean.append(url)

    clean.sort(key=_image_priority, reverse=True)
    return clean[:limit]


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


def assign_images_to_leads(leads: List[dict], page_images: List[str], max_per_lead: int | None = None) -> None:
    cap = max_per_lead if max_per_lead is not None else MAX_PROPERTY_IMAGES
    pool = list(page_images)
    for lead in leads:
        existing = lead.get("images") or []
        if existing:
            lead["images"] = existing[:cap]
            continue
        assigned: List[str] = []
        while pool and len(assigned) < cap:
            assigned.append(pool.pop(0))
        if assigned:
            lead["images"] = assigned


def is_portal_index_url(url: str) -> bool:
    lower = url.lower().rstrip("/")
    if re.search(r"/viviendas-[^/]+\.htm$", lower):
        return True
    if lower.endswith(("/selinmueble.htm", "/buscador.htm")):
        return True
    if lower.endswith(("/l", "/listado", "/listado.htm")):
        return True
    if re.search(r"/venta/pisos-[^/]+$", lower):
        return True
    if re.search(r"/comprar/viviendas/[^/]+/todas-las-zonas", lower):
        return True
    if re.search(r"/comprar-vivienda-en-[^/]+$", lower):
        return True
    if re.search(r"/venta/[^/]+$", lower):
        return True
    return False
