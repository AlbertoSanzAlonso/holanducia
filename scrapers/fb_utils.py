"""Utilidades para filtrado y enriquecimiento de posts de Facebook."""
import re
from typing import Any, Dict, Optional

from scrapers.portal_utils import is_facebook_post_url

PROPERTY_TYPES = (
    "piso", "casa", "vivienda", "chalet", "inmueble", "apartamento",
    "ático", "atico", "duplex", "dúplex", "estudio", "loft", "finca",
    "bungalow", "adosado", "townhouse", "local comercial", "local ",
    "garaje", "plaza de garaje", "trastero", "terreno", "parcela",
    "nave", "oficina", "habitacion", "habitación", "dormitorio",
    # English (Costa del Sol expat groups)
    "apartment", "flat", "house", "villa", "penthouse", "studio",
    "property", "bedroom", "bedrooms", "bed", "beds", "bath", "baths",
    "town house", "semi-detached", "detached", "terraced",
    "plot", "land", "garage", "parking", "storage room",
)

LISTING_INTENTS = (
    "se vende", "se alquila", "en venta", "en alquiler", "vendo", "alquilo",
    "alquiler", "venta", "precio", "€", "euro", "euros", "mensualidad",
    "comunidad de propietarios", "sin comision", "particular vende",
    "oportunidad", "rebajado", "urgente venta", "busco inquilino",
    # English (Costa del Sol expat groups)
    "for sale", "for rent", "to rent", "long term", "short term",
    "reduced", "bargain", "investment", "opportunity",
    "€", "euros", "euro", "price", "priced", "monthly",
    "private sale", "no agents", "direct sale",
)

NON_LISTING_HINTS = (
    "producto", "productos", "excelentes", "recomiendo", "recomendación",
    "servicio", "restaurante", "tienda", "oferta de trabajo", "busco empleo",
    "contrato", "curriculum", "coche", "moto", "mascota", "perdido", "encontrado",
    "gracias por", "felicidades", "buenos días", "buenas tardes", "meme", "broma",
    "extrañando", "clases de", "taller de", "evento", "fiesta", "sorteo",
    "whatsapp solo", "información sin", "consulta general",
)


def is_property_listing_text(text: str) -> bool:
    """Filtro estricto: tipo de inmueble + intención de anuncio."""
    lower = (text or "").lower()
    if len(lower) < 50:
        return False

    if any(hint in lower for hint in NON_LISTING_HINTS):
        has_property = any(t in lower for t in PROPERTY_TYPES)
        has_price = bool(extract_price_from_text(text))
        if has_property and has_price:
            return True
        has_intent = any(i in lower for i in ("vendo", "alquilo", "se vende", "se alquila", "en venta", "en alquiler"))
        if not (has_property and has_intent):
            return False

    has_type = any(t in lower for t in PROPERTY_TYPES)
    has_intent = any(i in lower for i in LISTING_INTENTS)
    has_price = bool(extract_price_from_text(text))

    if not has_type:
        return False
    if not has_intent and not has_price:
        return False
    return True


def looks_like_real_estate(text: str) -> bool:
    return is_property_listing_text(text)


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
        r"(?:precio|pvp|venta|alquiler)[:\s]*(\d{1,3}(?:\.\d{3})+|\d{3,7})",
        r"(\d{2,3})\s*k\b",
        r"(\d{2,3})\s*mil\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = match.group(1).replace(".", "").replace(",", ".")
            try:
                value = float(raw)
                if "k" in pattern or "mil" in pattern:
                    value *= 1000
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


def extract_garage_spots_from_text(text: str) -> Optional[int]:
    if not text:
        return None
    patterns = [
        r"(\d+)\s*(?:plazas?\s*(?:de\s*)?(?:garaje|parking|aparcamiento))",
        r"(?:garaje|parking|aparcamiento)\s*(?:de\s*)?(\d+)\s*plazas?",
        r"(\d+)\s*(?:coches?|vehiculos?|cocheras?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            spots = int(match.group(1))
            if 1 <= spots <= 10:
                return spots
    if re.search(r"(?:tiene|con|incluye|dispone de)\s*(?:garaje|parking|aparcamiento|plaza)", text, re.IGNORECASE):
        return 1
    if re.search(r"\bgaraje\b|\bparking\b|\bplaza de garaje\b", text, re.IGNORECASE):
        return 1
    return None


def extract_floor_from_text(text: str) -> Optional[int]:
    if not text:
        return None
    if re.search(r"\bbajo\b", text, re.IGNORECASE):
        return 0
    if re.search(r"\b(?:ático|atico|penthouse)\b", text, re.IGNORECASE):
        return 99
    patterns = [
        r"(\d+)[º°ª]\s*(?:planta|piso)",
        r"(?:planta|piso)\s*(\d+)",
        r"(\d+)[º°ª](?:\s|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            floor = int(match.group(1))
            if 1 <= floor <= 50:
                return floor
    return None


def extract_trastero_from_text(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(
        r"\b(?:trastero|almacén|almacen|bodega|despensa)\b",
        text, re.IGNORECASE,
    ))


def enrich_lead_from_raw(lead: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
    price = float(lead.get("price") or 0)
    if price <= 0:
        extracted = extract_price_from_text(raw_text)
        if extracted:
            lead["price"] = extracted

    if not lead.get("rooms"):
        rooms = extract_rooms_from_text(raw_text)
        if rooms:
            lead["rooms"] = rooms

    if not lead.get("size_m2"):
        size = extract_size_m2_from_text(raw_text)
        if size:
            lead["size_m2"] = size

    if not lead.get("garage_spots"):
        spots = extract_garage_spots_from_text(raw_text)
        if spots is not None:
            lead["garage_spots"] = spots
            lead["has_parking"] = spots > 0

    if not lead.get("floor") and lead.get("floor") != 0:
        floor = extract_floor_from_text(raw_text)
        if floor is not None:
            lead["floor"] = floor

    if not lead.get("has_trastero"):
        if extract_trastero_from_text(raw_text):
            lead["has_trastero"] = True

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
    if lead.get("garage_spots"):
        score += 1
    if lead.get("floor") is not None:
        score += 1
    score += 1 if lead.get("has_terrace") else 0
    score += 1 if lead.get("has_pool") else 0
    score += 1 if lead.get("has_garden") else 0
    score += 1 if lead.get("has_trastero") else 0
    if lead.get("images"):
        score += 2
    if is_facebook_post_url(lead.get("url") or ""):
        score += 1
    if is_property_listing_text(raw_text):
        score += 2
    return score


def is_quality_facebook_lead(lead: Dict[str, Any], raw_text: str, *, min_score: int = 4) -> bool:
    if not is_property_listing_text(raw_text):
        return False
    price = float(lead.get("price") or 0)
    has_photo = bool(lead.get("images"))
    has_data = bool(lead.get("rooms") or lead.get("size_m2"))
    if price <= 0 and not has_photo and not has_data:
        return False
    score = quality_score(lead, raw_text)
    passed = score >= min_score
    if not passed:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            "FB calidad baja (score=%s/%s): price=%s rooms=%s size=%s baths=%s garage=%s floor=%s terr=%s pool=%s garden=%s trastero=%s imgs=%s url=%s txt=%s — %s",
            score,
            min_score,
            price,
            lead.get("rooms"),
            lead.get("size_m2"),
            lead.get("bathrooms"),
            lead.get("garage_spots"),
            lead.get("floor"),
            lead.get("has_terrace"),
            lead.get("has_pool"),
            lead.get("has_garden"),
            lead.get("has_trastero"),
            bool(lead.get("images")),
            bool(lead.get("url")),
            is_property_listing_text(raw_text),
            (lead.get("title") or raw_text[:80]),
        )
    return passed
