import re
from urllib.parse import urlparse, urljoin

from scrapers.image_utils import is_portal_index_url

PORTAL_HOSTS = ("pisos.com", "fotocasa.es", "habitaclia.com", "idealista.com")

DETAIL_PATH_HINTS = (
    "/comprar/",
    "/vivienda/",
    "/inmueble/",
    "/anuncio/",
    "/chalet",
    "/piso-",
    "/atico",
    "/local-",
    "/duplex",
    "/casa-",
)


def normalize_portal_url(raw: str, page_url: str = "") -> str:
    raw = (raw or "").strip().split("#")[0].split("?")[0]
    if not raw:
        return ""
    if raw.startswith("/"):
        if not page_url:
            return ""
        parsed = urlparse(page_url)
        raw = urljoin(f"{parsed.scheme}://{parsed.netloc}", raw)
    if raw.startswith("http"):
        return raw.rstrip("/")
    return ""


def is_listing_detail_url(url: str) -> bool:
    url = normalize_portal_url(url)
    if not url or is_portal_index_url(url):
        return False
    host = urlparse(url).netloc.lower()
    if not any(portal in host for portal in PORTAL_HOSTS):
        return False
    path = urlparse(url).path.lower()
    return any(hint in path for hint in DETAIL_PATH_HINTS)


def is_valid_listing_url(url: str) -> bool:
    return is_listing_detail_url(url) and "#lead-" not in url


def external_id_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    if not path:
        return url
    slug = path.split("/")[-1]
    return slug or path.replace("/", "-")


def extract_listing_urls(html: str = "", markdown: str = "", page_url: str = "") -> list[str]:
    candidates: list[str] = []

    for text in (html or "", markdown or ""):
        candidates.extend(re.findall(r'href=["\']([^"\']+)["\']', text, flags=re.I))
        candidates.extend(re.findall(r"\((https?://[^)\s]+)\)", text))
        candidates.extend(re.findall(r"https?://[^\s\"'<>]+", text))

    seen: set[str] = set()
    listing_urls: list[str] = []
    for raw in candidates:
        url = normalize_portal_url(raw, page_url)
        if not url or url in seen:
            continue
        seen.add(url)
        if is_listing_detail_url(url):
            listing_urls.append(url)

    return listing_urls


def assign_listing_urls_to_leads(leads: list[dict], listing_urls: list[str]) -> None:
    pool = list(listing_urls)
    for lead in leads:
        if is_valid_listing_url(lead.get("url", "")):
            continue
        if pool:
            lead["url"] = pool.pop(0)


def resolve_lead_identity(lead: dict, base_url: str) -> tuple[str, str]:
    from scrapers.agency.curator import make_lead_dedup_key

    candidate = lead.get("url") or ""
    if is_valid_listing_url(candidate):
        return candidate, external_id_from_url(candidate)

    if is_listing_detail_url(base_url):
        return base_url.rstrip("/"), external_id_from_url(base_url)

    dedup_key = make_lead_dedup_key(lead.get("title", ""), lead.get("price", 0))
    return f"{base_url}#lead-{dedup_key}", dedup_key


def prioritize_portal_urls(urls: list[str]) -> list[str]:
    detail = [u for u in urls if is_listing_detail_url(u)]
    index = [u for u in urls if is_portal_index_url(u)]
    other = [u for u in urls if u not in detail and u not in index]
    if detail:
        return list(dict.fromkeys(detail))
    return list(dict.fromkeys(index + other))
