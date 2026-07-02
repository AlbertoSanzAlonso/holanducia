import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

PORTAL_TEMPLATES = {
    "fotocasa": "https://www.fotocasa.es/es/comprar/viviendas/{city}-provincia/todas-las-zonas/l",
    "habitaclia": "https://www.habitaclia.com/comprar-vivienda-en-{city}/listado.htm",
    "pisos.com": "https://www.pisos.com/venta/pisos-{city}/",
}


class DatabaseConnector:
    def __init__(self, api_url: str = None, **_ignored):
        self.api_url = (api_url or os.getenv("API_URL", "http://localhost:9000")).rstrip("/")

    async def upsert_property(self, property_data: Dict[str, Any]):
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self.api_url}/api/properties", json=property_data)
            if response.status_code >= 400:
                logger.error("DB Insert Error %s: %s", response.status_code, response.text)
            response.raise_for_status()
            return response.json()

    async def analyze_property(self, property_data: Dict[str, Any], market_avg: float):
        score = 0
        reasons = []
        price = float(property_data.get("price") or 0)
        if price and price < market_avg * 100:
            score += 30
            reasons.append("Precio por debajo del mercado estimado")
        if property_data.get("is_individual"):
            score += 20
            reasons.append("Particular")
        return {"score": score, "reasons": reasons}

    async def enrich_catastro(self, address: str, city: str):
        return None

    async def get_settings(self) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{self.api_url}/api/settings")
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error("Failed to fetch settings: %s", e)
                return None

    async def check_property_exists(self, url: str) -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{self.api_url}/api/properties")
                response.raise_for_status()
                return any(item.get("url") == url for item in response.json())
            except Exception:
                return False

    async def upsert_scraping_status(self, status: str, message: str):
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                latest = await client.get(f"{self.api_url}/api/scraping-requests/latest")
                latest.raise_for_status()
                data = latest.json()
                if not data:
                    return
                await client.patch(
                    f"{self.api_url}/api/scraping-requests/{data['id']}",
                    json={"status": status, "error_message": message},
                )
                logger.info("Status reported to DB: %s", status)
            except Exception as e:
                logger.error("Failed to report scraping status: %s", e)


def build_portal_urls(settings: Optional[Dict[str, Any]]) -> List[str]:
    settings = settings or {}
    urls = settings.get("portal_urls") or []
    if isinstance(urls, str):
        urls = [u.strip() for u in urls.split(",") if u.strip()]
    if urls:
        return urls

    cities = settings.get("cities") or ["malaga"]
    portals = [p.strip().lower() for p in (settings.get("portals") or "").split(",") if p.strip()]
    built = []

    for city in cities:
        city_slug = city.strip().lower().replace(" ", "-")
        for portal in portals:
            if portal in {"facebook", "catastro"}:
                continue
            if "fotocasa" in portal:
                built.append(PORTAL_TEMPLATES["fotocasa"].format(city=city_slug))
            elif "habitaclia" in portal:
                built.append(PORTAL_TEMPLATES["habitaclia"].format(city=city_slug))
            elif "pisos" in portal:
                built.append(PORTAL_TEMPLATES["pisos.com"].format(city=city_slug))

    return list(dict.fromkeys(built))
