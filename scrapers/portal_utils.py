import logging
import re
import unicodedata
from urllib.parse import urlparse, urljoin

from scrapers.image_utils import is_portal_index_url

logger = logging.getLogger(__name__)

PORTAL_HOSTS = ("pisos.com", "fotocasa.es", "habitaclia.com", "idealista.com")
MAX_DETAIL_URLS_PER_PORTAL = 50

# Ficha Habitaclia: comprar-piso-malaga-centro-i55621000000139.htm
HABITACLIA_DETAIL_RE = re.compile(
    r"(?:https?://(?:www\.)?habitaclia\.com/)?comprar-[^\s\"'<>]+-i\d+\.htm",
    re.I,
)
HABITACLIA_LEGACY_LISTADO_RE = re.compile(
    r"^https?://(?:www\.)?habitaclia\.com/comprar-vivienda-en-([^/]+)/listado\.htm$",
    re.I,
)
# Ficha Fotocasa: /es/comprar/vivienda/{zona}/{slug}/{id}/d
FOTOCASA_DETAIL_RE = re.compile(
    r"(?:https?://(?:www\.)?fotocasa\.es)?/es/comprar/vivienda/[^\"'\s<>]+/\d+(?:/\d+)?(?:/d)?",
    re.I,
)


def _city_slug(raw: str) -> str:
    normalized = unicodedata.normalize("NFD", (raw or "").strip())
    ascii_slug = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    return ascii_slug.lower().replace(" ", "-")


def normalize_habitaclia_index_url(url: str) -> str:
    """Migra índices Habitaclia obsoletos (listado.htm 404) al formato actual."""
    clean = (url or "").strip().split("?")[0].rstrip("/")
    if not clean:
        return url

    match = HABITACLIA_LEGACY_LISTADO_RE.match(clean)
    if match:
        return f"https://www.habitaclia.com/viviendas-{_city_slug(match.group(1))}.htm"

    legacy_hub = re.match(
        r"^https?://(?:www\.)?habitaclia\.com/comprar-vivienda-en-([^/.]+)/selinmueble\.htm$",
        clean,
        re.I,
    )
    if legacy_hub:
        return f"https://www.habitaclia.com/viviendas-{_city_slug(legacy_hub.group(1))}.htm"

    return url


def normalize_portal_urls(urls: list[str]) -> list[str]:
    normalized: list[str] = []
    for raw in urls or []:
        url = (raw or "").strip()
        if not url:
            continue
        migrated = normalize_habitaclia_index_url(url)
        if migrated != url:
            logger.info("URL Habitaclia migrada: %s → %s", url[:80], migrated[:80])
        normalized.append(migrated)
    return list(dict.fromkeys(normalized))


def portal_host(url: str) -> str:
    host = urlparse(normalize_portal_url(url) or url).netloc.lower().replace("www.", "")
    for portal in PORTAL_HOSTS:
        if portal in host:
            return portal
    return host or "unknown"

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
    raw = (raw or "").strip().strip(")'\"[],;")
    raw = raw.split("#")[0].split("?")[0]
    if not raw:
        return ""
    if raw.startswith("/"):
        if not page_url:
            return ""
        parsed = urlparse(page_url)
        raw = urljoin(f"{parsed.scheme}://{parsed.netloc}", raw)
    if raw.startswith("http"):
        return raw.rstrip("/).")
    return ""


def is_listing_detail_url(url: str) -> bool:
    url = normalize_portal_url(url)
    if not url or is_portal_index_url(url):
        return False
    host = urlparse(url).netloc.lower()
    if not any(portal in host for portal in PORTAL_HOSTS):
        return False
    path = urlparse(url).path.lower()

    if "pisos.com" in host:
        return path.startswith("/comprar/") and len(path.split("/")) >= 3

    if "fotocasa.es" in host:
        return bool(re.search(r"/es/comprar/vivienda/.+/\d+", path))

    if "habitaclia.com" in host:
        return bool(re.search(r"-i\d+\.htm$", path)) or bool(re.search(r"/\d+\.htm$", path))

    return any(hint in path for hint in DETAIL_PATH_HINTS)


def normalize_facebook_post_url(url: str) -> str:
    url = normalize_portal_url(url)
    if not url or "facebook.com" not in url.lower():
        return ""
    return url.split("?")[0].rstrip("/")


def is_facebook_post_url(url: str) -> bool:
    url = normalize_facebook_post_url(url) or normalize_portal_url(url)
    if not url or "facebook.com" not in url.lower():
        return False
    lower = url.lower()
    return any(
        token in lower
        for token in (
            "/posts/",
            "/permalink/",
            "story_fbid",
            "multi_permalinks",
            "/photo/",
            "fbid=",
        )
    )


def is_valid_listing_url(url: str) -> bool:
    return is_listing_detail_url(url) or is_facebook_post_url(url)


def external_id_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    if not path:
        return url
    slug = path.split("/")[-1]
    result = slug or path.replace("/", "-")
    return result[:120]  # DB varchar limit


def extract_listing_urls(html: str = "", markdown: str = "", page_url: str = "") -> list[str]:
    candidates: list[str] = []
    combined = f"{html or ''}\n{markdown or ''}"

    for text in (html or "", markdown or ""):
        candidates.extend(re.findall(r'href=["\']([^"\']+)["\']', text, flags=re.I))
        candidates.extend(re.findall(r"\((https?://[^)\s]+)\)", text))
        candidates.extend(re.findall(r"https?://[^\s\"'<>]+", text))

    if "habitaclia.com" in (page_url or "").lower() or "habitaclia.com" in combined.lower():
        candidates.extend(HABITACLIA_DETAIL_RE.findall(combined))

    if "fotocasa.es" in (page_url or "").lower() or "fotocasa.es" in combined.lower():
        candidates.extend(FOTOCASA_DETAIL_RE.findall(combined))

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

    candidate = normalize_facebook_post_url(lead.get("url") or "") or (lead.get("url") or "")
    if candidate and "#lead-" not in candidate and is_valid_listing_url(candidate):
        return candidate, external_id_from_url(candidate)

    if is_listing_detail_url(base_url):
        return base_url.rstrip("/"), external_id_from_url(base_url)

    dedup_key = make_lead_dedup_key(lead.get("title", ""), lead.get("price", 0))
    group_base = normalize_portal_url(base_url).rstrip("/")
    if "facebook.com/groups" in group_base.lower():
        return f"{group_base}#lead-{dedup_key}", dedup_key

    return f"{base_url}#lead-{dedup_key}", dedup_key


def prioritize_portal_urls(urls: list[str]) -> list[str]:
    """Por portal: fichas primero (con límite), si no hay fichas usa la página índice."""
    by_host: dict[str, list[str]] = {}
    for url in urls:
        by_host.setdefault(portal_host(url), []).append(url)

    ordered: list[str] = []
    for host_urls in by_host.values():
        detail = [u for u in host_urls if is_listing_detail_url(u)]
        index = [u for u in host_urls if is_portal_index_url(u)]
        other = [u for u in host_urls if u not in detail and u not in index]

        if detail:
            ordered.extend(dict.fromkeys(detail[:MAX_DETAIL_URLS_PER_PORTAL]))
        if index:
            ordered.extend(dict.fromkeys(index))
        if not detail and not index:
            ordered.extend(dict.fromkeys(other))

    return list(dict.fromkeys(ordered))


def interleave_portal_urls(urls: list[str]) -> list[str]:
    """Alterna URLs entre portales para que ninguno monopolice la cuota."""
    buckets: dict[str, list[str]] = {}
    for url in urls:
        buckets.setdefault(portal_host(url), []).append(url)

    if len(buckets) <= 1:
        return urls

    hosts = list(buckets.keys())
    result: list[str] = []
    while any(buckets[h] for h in hosts):
        for host in hosts:
            if buckets[host]:
                result.append(buckets[host].pop(0))
    return result
