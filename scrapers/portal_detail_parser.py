"""Extracción estructurada de fichas de portales (pisos.com, fotocasa, habitaclia)."""
import re
from typing import Any, Dict, List, Optional

from scrapers.portal_utils import portal_host


def _first_match(patterns: List[str], text: str, flags=re.I | re.M) -> Optional[str]:
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            return m.group(1).strip()
    return None


def _parse_int(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"(\d+)", text.replace(".", ""))
    return int(m.group(1)) if m else None


def _parse_price(text: str) -> float:
    m = re.search(r"(\d[\d.\s]*\d|\d+)\s*€", text.replace("\u00a0", " "))
    if not m:
        return 0.0
    raw = re.sub(r"[^\d]", "", m.group(1))
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _section(text: str, header: str, until_headers: Optional[List[str]] = None) -> str:
    until = "|".join(re.escape(h) for h in (until_headers or []))
    pat = rf"{re.escape(header)}\s*\n(.*?)(?=\n(?:{until})\s*\n|\Z)"
    m = re.search(pat, text, re.I | re.S)
    return m.group(1).strip() if m else ""


def _bool_feature(text: str, keywords: List[str]) -> bool:
    lower = text.lower()
    return any(kw.lower() in lower for kw in keywords)


def parse_pisos_com(markdown: str, url: str, images: Optional[List[str]] = None) -> Dict[str, Any]:
    text = markdown or ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    title = None
    for ln in lines[:15]:
        if re.search(r"\b(en venta|en alquiler)\b", ln, re.I) and len(ln) > 20:
            title = ln
            break
    if not title:
        title = lines[0] if lines else "Anuncio pisos.com"

    location_line = ""
    for i, ln in enumerate(lines[:20]):
        if title and ln == title and i + 1 < len(lines):
            location_line = lines[i + 1]
            break

    city = None
    neighborhood = None
    if location_line:
        if "(" in location_line:
            neighborhood = location_line.split("(")[0].strip(" -–")
            city = location_line.split("(")[-1].rstrip(")").strip()
        else:
            city = location_line

    chars_block = _section(text, "Características", ["Certificado", "¿Te ha gustado", "Publicidad"])
    desc_block = _section(text, "Descripción", ["Características", "Certificado", "¿Te ha gustado"])

    size_m2 = _parse_int(
        _first_match(
            [
                r"Superficie construida:\s*(\d+)\s*m",
                r"Superficie útil:\s*(\d+)\s*m",
                r"(\d+)\s*m²\s*construid",
            ],
            chars_block or text,
        )
    )
    rooms = _parse_int(_first_match([r"Habitaciones:\s*(\d+)", r"(\d+)\s*habitacion"], chars_block or text))
    bathrooms = _parse_int(_first_match([r"Baños:\s*(\d+)", r"(\d+)\s*baño"], chars_block or text))

    price = _parse_price(text)
    if price <= 0:
        price = _parse_price(chars_block)

    ref = _first_match([r"Referencia:\s*(\S+)"], chars_block or text)
    year_hint = _first_match([r"Antigüedad:\s*(.+)"], chars_block or text)

    description_parts = []
    if desc_block:
        description_parts.append(desc_block)
    if chars_block:
        description_parts.append("\n--- Características ---\n" + chars_block)
    description = "\n\n".join(description_parts).strip() or text[:8000]

    agency_markers = ("inmobiliaria", "gestión inmobiliaria", "whatsapp", "concertar una visita", "mamboinmobiliaria")
    is_agency = _bool_feature(text, agency_markers)

    return {
        "title": title[:500],
        "price": price,
        "city": city,
        "neighborhood": neighborhood,
        "size_m2": size_m2,
        "rooms": rooms,
        "bathrooms": bathrooms,
        "description": description[:15000],
        "catastro_ref": ref,
        "year_built": None,
        "has_parking": _bool_feature(chars_block or text, ["garaje", "parking", "aparcamiento"]),
        "has_terrace": _bool_feature(chars_block or text, ["terraza"]),
        "has_pool": _bool_feature(chars_block or text, ["piscina"]),
        "is_individual": not is_agency,
        "is_agency": is_agency,
        "images": (images or [])[:8],
        "url": url.rstrip("/"),
        "source": "pisos.com",
        "_parse_meta": {"year_hint": year_hint, "parser": "pisos.com"},
    }


def parse_fotocasa(markdown: str, url: str, images: Optional[List[str]] = None) -> Dict[str, Any]:
    text = markdown or ""
    title = _first_match([r"^#\s+(.+)$", r"^(.{20,120}(?:venta|alquiler).*)$"], text) or "Anuncio Fotocasa"
    price = _parse_price(text)
    size_m2 = _parse_int(_first_match([r"(\d+)\s*m²", r"Superficie[^\d]*(\d+)"], text))
    rooms = _parse_int(_first_match([r"(\d+)\s*hab", r"Habitaciones[^\d]*(\d+)"], text))
    bathrooms = _parse_int(_first_match([r"(\d+)\s*baño", r"Baños[^\d]*(\d+)"], text))

    return {
        "title": title[:500],
        "price": price,
        "city": _first_match([r" en ([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s-]+?)(?:,|\n|$)"], text),
        "neighborhood": None,
        "size_m2": size_m2,
        "rooms": rooms,
        "bathrooms": bathrooms,
        "description": text[:15000],
        "has_parking": _bool_feature(text, ["garaje", "parking"]),
        "has_terrace": _bool_feature(text, ["terraza", "balcón"]),
        "has_pool": _bool_feature(text, ["piscina"]),
        "is_individual": not _bool_feature(text, ["inmobiliaria", "agency"]),
        "is_agency": _bool_feature(text, ["inmobiliaria", "profesional"]),
        "images": (images or [])[:8],
        "url": url.rstrip("/"),
        "source": "fotocasa.es",
        "_parse_meta": {"parser": "fotocasa.es"},
    }


def parse_habitaclia(markdown: str, url: str, images: Optional[List[str]] = None) -> Dict[str, Any]:
    text = markdown or ""
    title = _first_match([r"^#\s+(.+)$", r"^(.{15,120})$"], text) or "Anuncio Habitaclia"
    return {
        "title": title[:500],
        "price": _parse_price(text),
        "city": _first_match([r" en ([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s-]+)"], text),
        "neighborhood": None,
        "size_m2": _parse_int(_first_match([r"(\d+)\s*m²", r"Superf[^\d]*(\d+)"], text)),
        "rooms": _parse_int(_first_match([r"(\d+)\s*hab"], text)),
        "bathrooms": _parse_int(_first_match([r"(\d+)\s*baño"], text)),
        "description": text[:15000],
        "has_parking": _bool_feature(text, ["garaje", "parking"]),
        "has_terrace": _bool_feature(text, ["terraza"]),
        "has_pool": _bool_feature(text, ["piscina"]),
        "is_individual": not _bool_feature(text, ["inmobiliaria"]),
        "is_agency": _bool_feature(text, ["inmobiliaria"]),
        "images": (images or [])[:8],
        "url": url.rstrip("/"),
        "source": "habitaclia.com",
        "_parse_meta": {"parser": "habitaclia.com"},
    }


PARSERS = {
    "pisos.com": parse_pisos_com,
    "fotocasa.es": parse_fotocasa,
    "habitaclia.com": parse_habitaclia,
}


def parse_portal_detail(
    url: str,
    markdown: str,
    *,
    html: str = "",
    images: Optional[List[str]] = None,
) -> Dict[str, Any]:
    host = portal_host(url)
    parser = PARSERS.get(host)
    if parser:
        return parser(markdown, url, images)
    return {
        "title": None,
        "price": _parse_price(markdown or ""),
        "description": (markdown or "")[:15000],
        "images": (images or [])[:8],
        "url": url.rstrip("/"),
        "source": host,
        "_parse_meta": {"parser": "generic"},
    }


def is_card_snippet(title: Optional[str], description: Optional[str]) -> bool:
    """Detecta datos extraídos de tarjeta de listado, no de ficha completa."""
    blob = f"{title or ''} {description or ''}".lower()
    markers = ("fotos", "tour", "avísame si baja", "calcula tu hipoteca", "oportunidad")
    hits = sum(1 for m in markers if m in blob)
    return hits >= 2
