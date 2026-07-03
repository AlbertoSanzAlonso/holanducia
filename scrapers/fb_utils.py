"""Utilidades para filtrado y enriquecimiento de posts de Facebook."""
import re
from typing import Any, Dict, Optional

from scrapers.portal_utils import is_facebook_post_url

# Requiere al menos una keyword fuerte (no basta con "euro" o "precio" sueltos)
STRONG_REAL_ESTATE_KEYWORDS = (
    "piso", "casa", "vivienda", "chalet", "inmueble", "apartamento",
    "ático", "atico", "duplex", "dúplex", "estudio", "loft", "finca",
    "alquiler", "se alquila", "se vende", "vendo", "venta",
    "habitacion", "habitación", "dormitorio", " dorm ", " hab ", " habs",
    "m2", "m²", " metros", "garaje", "trastero", "terraza", "ático",
    "reformado", "amueblado", "comunidad de propietarios",
)

WEAK_REAL_ESTATE_KEYWORDS = (
    "€", "euro", "precio", "particular", "inmobiliaria", "oportunidad",
    "urgente", "terreno", "local comercial", "bungalow", "townhouse",
)

# Señales de que NO es inmobiliario
NON_REAL_ESTATE_HINTS = (
    "producto", "productos", "excelentes", "recomiendo", "servicio",
    "restaurante", "tienda", "oferta de trabajo", "busco empleo",
    "coche", "moto", "mascota", "perdido", "encontrado", "gracias por",
    "felicidades", "buenos días", "buenas tardes", "meme", "broma",
)


def looks_like_real_estate(text: str) -> bool:
    lower = (text or "").lower()
    if len(lower) < 40:
        return False
    if any(hint in lower for hint in NON_REAL_ESTATE_HINTS):
        if not any(k in lower for k in ("piso", "casa", "vivienda", "alquiler", "vendo", "venta", "inmueble")):
            return False
    if any(k in lower for k in STRONG_REAL_ESTATE_KEYWORDS):
        return True
    # Débil: al menos 2 keywords débiles + patrón de precio
    weak_hits = sum(1 for k in WEAK_REAL_ESTATE_KEYWORDS if k in lower)
    return weak_hits >= 2 and bool(extract_price_from_text(text))


def extract_price_from_text(text: str) -> Optional[float]:
    if not text:
        return None
    patterns = [
        r"(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?)\s*€",
        r"(\d{4,7})\s*€",
        r"€\s*(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d{3,7})",
        r"(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d{3,7})\s*euros?",
        r"(\d{3,5})\s*€\s*/\s*mes",
        r"(\d{3,5})\s*€/mes",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = match.group(1).replace(".", "").replace(",", ".")
            try:
                value = float(raw)
                if 100 <= value <= 50_000_000:
                    return value
            except ValueError:
                continue
    return None


def extract_rooms_from_text(text: str) -> Optional[int]:
    if not text:
        return None
    patterns = [
        r"(\d+)\s*(?:hab(?:itaciones?)?|dorm(?:itorios?)?|habs?)\b",
        r"\b(\d+)\s*d\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            rooms = int(match.group(1))
            if 1 <= rooms <= 20:
                return rooms
    return None


def extract_size_m2_from_text(text: str) -> Optional[float]:
    if not text:
        return None
    match = re.search(r"(\d{2,4})\s*m[²2]\b", text, re.IGNORECASE)
    if match:
        size = float(match.group(1))
        if 15 <= size <= 5000:
            return size
    return None


def enrich_lead_from_raw(lead: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
    if not lead.get("price"):
        price = extract_price_from_text(raw_text)
        if price:
            lead["price"] = price

    if not lead.get("rooms"):
        rooms = extract_rooms_from_text(raw_text)
        if rooms:
            lead["rooms"] = rooms

    if not lead.get("size_m2"):
        size = extract_size_m2_from_text(raw_text)
        if size:
            lead["size_m2"] = size

    desc = (lead.get("description") or "").strip()
    title = (lead.get("title") or "").strip()
    if len(desc) < 60 or desc.lower() == title.lower() or desc == "None":
        lead["description"] = raw_text[:2000].strip()

    return lead


def quality_score(lead: Dict[str, Any], raw_text: str) -> int:
    score = 0
    if (lead.get("price") or 0) > 0:
        score += 2
    if lead.get("rooms"):
        score += 1
    if lead.get("size_m2"):
        score += 1
    if lead.get("bathrooms"):
        score += 1
    if lead.get("images"):
        score += 2
    if is_facebook_post_url(lead.get("url") or ""):
        score += 2
    if looks_like_real_estate(raw_text):
        score += 1
    return score


def is_quality_facebook_lead(lead: Dict[str, Any], raw_text: str, *, min_score: int = 3) -> bool:
    if not looks_like_real_estate(raw_text):
        return False
    return quality_score(lead, raw_text) >= min_score
