import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from scrapers.portal_utils import normalize_portal_urls

logger = logging.getLogger(__name__)

PORTAL_TEMPLATES = {
    "fotocasa": "https://www.fotocasa.es/es/comprar/viviendas/{city}-provincia/todas-las-zonas/l",
    "habitaclia": "https://www.habitaclia.com/viviendas-{city}.htm",
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

    async def upsert_property_with_embedding(self, property_data: Dict[str, Any]) -> bool:
        """Guarda en Postgres vía API y asegura embedding vectorial para consultas."""
        try:
            result = await self.upsert_property(property_data)
            prop_id = result.get("id")
            if not prop_id:
                return False

            async with httpx.AsyncClient(timeout=45.0) as client:
                embed_resp = await client.post(f"{self.api_url}/api/properties/{prop_id}/embed")
                if embed_resp.status_code == 200:
                    logger.info("Postgres + vector OK — property #%s", prop_id)
                elif embed_resp.status_code == 503:
                    logger.warning(
                        "Postgres OK, vector omitido (OPENAI_API_KEY no configurada) — #%s",
                        prop_id,
                    )
                else:
                    logger.warning(
                        "Postgres OK, embedding falló (%s): %s",
                        embed_resp.status_code,
                        embed_resp.text[:200],
                    )
            return True
        except Exception as e:
            logger.error("upsert_property_with_embedding falló: %s", e)
            return False

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
        urls, _ = await self.get_property_index()
        return url in urls

    async def get_property_index(self) -> tuple[set[str], set[str]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{self.api_url}/api/properties")
                response.raise_for_status()
                items = response.json()
                urls = {item["url"] for item in items if item.get("url")}
                external_ids = {item["external_id"] for item in items if item.get("external_id")}
                return urls, external_ids
            except Exception as e:
                logger.error("Failed to load property index: %s", e)
                return set(), set()

    async def find_similar_property(
        self,
        lead: Dict[str, Any],
        *,
        exclude_url: Optional[str] = None,
        min_similarity: float = 0.75,
    ) -> Optional[Dict[str, Any]]:
        text = self._lead_to_search_text(lead)
        if not text.strip():
            return None

        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                response = await client.post(
                    f"{self.api_url}/api/properties/similar",
                    json={"text": text, "limit": 3, "min_similarity": min_similarity},
                )
                if response.status_code != 200:
                    return None
                for match in response.json():
                    if exclude_url and match.get("url") == exclude_url:
                        continue
                    return match
            except Exception as e:
                logger.debug("Similarity search unavailable: %s", e)
        return None

    @staticmethod
    def _lead_to_search_text(lead: Dict[str, Any]) -> str:
        parts = [
            lead.get("title"),
            f"Precio: {lead.get('price')} EUR" if lead.get("price") else None,
            f"Ciudad: {lead.get('city')}" if lead.get("city") else None,
            lead.get("description"),
            f"{lead.get('rooms')} habitaciones" if lead.get("rooms") else None,
        ]
        return " | ".join(str(p) for p in parts if p)

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

    async def get_property_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.api_url}/api/properties/by-url",
                    params={"url": url},
                )
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                logger.debug("get_property_by_url falló: %s", e)
        return None

    async def start_sync_run(self, sources: List[str]) -> int:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.api_url}/api/sync/start",
                json={"sources": sources},
            )
            response.raise_for_status()
            return response.json()["sync_run_id"]

    async def finalize_sync_run(
        self,
        sync_run_id: int,
        *,
        seen_urls: List[str],
        sources: List[str],
        stats: Dict[str, Any],
        deactivate_missing: bool = True,
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.api_url}/api/sync/{sync_run_id}/finalize",
                json={
                    "seen_urls": seen_urls,
                    "sources": sources,
                    "stats": stats,
                    "deactivate_missing": deactivate_missing,
                },
            )
            response.raise_for_status()
            return response.json()


def build_portal_urls(settings: Optional[Dict[str, Any]]) -> List[str]:
    settings = settings or {}
    urls = settings.get("portal_urls") or []
    if isinstance(urls, str):
        urls = [u.strip() for u in urls.split(",") if u.strip()]
    if urls:
        return normalize_portal_urls(urls)

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

    return normalize_portal_urls(list(dict.fromkeys(built)))
