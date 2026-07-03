"""Utilidades para sync diario y detección de cambios."""
import hashlib
import json
from typing import Any, Dict


def content_hash(lead: Dict[str, Any]) -> str:
    payload = {
        "title": lead.get("title"),
        "price": lead.get("price"),
        "city": lead.get("city"),
        "neighborhood": lead.get("neighborhood"),
        "size_m2": lead.get("size_m2"),
        "rooms": lead.get("rooms"),
        "bathrooms": lead.get("bathrooms"),
        "description": (lead.get("description") or "")[:500],
        "images": (lead.get("images") or [])[:3],
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
