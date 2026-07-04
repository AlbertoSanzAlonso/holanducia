import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import httpx
import logging
import os
import sys
import redis

from scrapers.db_connector import DatabaseConnector
from scrapers.sync_context import is_sync_mode
from scrapers.image_utils import is_portal_index_url
from scrapers.portal_sniper_core import is_incomplete_portal_record
from scrapers.portal_utils import is_listing_detail_url, normalize_portal_url

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ESQUEMA ULTRA-PRECISO PARA RADIOGRAFÍA INMOBILIARIA
DEEP_PROPERTY_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Titular del anuncio"},
        "price": {"type": "number", "description": "PRECIO FINAL EN EUROS. OBLIGATORIO."},
        "city": {"type": "string", "description": "Ciudad o municipio principal"},
        "neighborhood": {"type": "string", "description": "Barrio, distrito o zona específica. OBLIGATORIO."},
        "address": {"type": "string", "description": "Calle y número si está disponible"},
        "size_m2": {"type": "number", "description": "Superficie útil o construida en m2 (solo el número)."},
        "rooms": {"type": "number", "description": "Número de dormitorios/habitaciones."},
        "bathrooms": {"type": "number", "description": "Número de baños"},
        "has_parking": {"type": "boolean", "description": "True si tiene parking/garaje"},
        "has_terrace": {"type": "boolean", "description": "True si tiene terraza/balcón"},
        "has_pool": {"type": "boolean", "description": "True si tiene piscina"},
        "is_individual": {"type": "boolean", "description": "True si el vendedor es un PARTICULAR"},
        "description": {"type": "string", "description": "Descripción completa"},
        "images": {"type": "array", "items": {"type": "string"}}
    }
}

class BaseScraper(ABC):
    def __init__(self, source_name: str, base_url: str, settings: Optional[dict] = None):
        self.source_name = source_name
        self.base_url = base_url
        self.settings = settings or {}
        self.results = []
        
        # Security: Keys MUST be in ENV
        self.firecrawl_key = os.getenv("FIRECRAWL_API_KEY")
        self.firecrawl_base = "https://api.firecrawl.dev/v1"
        
        # API del VPS (FastAPI)
        self.connector = DatabaseConnector(
            api_url=os.getenv("API_URL", "http://localhost:9000")
        )

        # Redis Deduplication Layer
        redis_host = os.getenv("REDIS_HOST", "redis") # "redis" because of docker-compose
        try:
            self.redis = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)
            logger.info(f"✅ Redis Deduplication active for {self.source_name}")
        except Exception as e:
            self.redis = None
            logger.warning(f"❌ Redis not available, deduplication disabled: {e}")

        self._known_db_urls: Optional[set[str]] = None

    def reset_db_url_cache(self) -> None:
        self._known_db_urls = None

    async def load_db_url_index(self) -> set[str]:
        if self._known_db_urls is None:
            urls, _ = await self.connector.get_property_index()
            self._known_db_urls = {
                (normalize_portal_url(u) or u).rstrip("/") for u in urls if u
            }
            logger.info("Índice BD cargado — %s URLs conocidas", len(self._known_db_urls))
        return self._known_db_urls

    def _normalize_url_key(self, url: str) -> str:
        return (normalize_portal_url(url) or url).rstrip("/")

    async def is_in_db(self, url: str) -> bool:
        if not is_listing_detail_url(url):
            return False
        known = await self.load_db_url_index()
        return self._normalize_url_key(url) in known

    @abstractmethod
    async def scrape(self):
        pass

    async def _needs_portal_rescrape(self, url: str) -> bool:
        if not is_listing_detail_url(url):
            return False
        try:
            prop = await self.connector.get_property_by_url(url)
            return is_incomplete_portal_record(prop)
        except Exception as e:
            logger.debug("No se pudo comprobar calidad de %s: %s", url[:60], e)
            return False

    async def is_already_scraped(self, url: str) -> bool:
        """Evita re-scrape (y gasto Firecrawl) si la ficha ya está en BD o Redis."""
        if is_sync_mode():
            return False
        if is_portal_index_url(url):
            return False
        if await self._needs_portal_rescrape(url):
            logger.info("♻️ Re-scrape ficha incompleta: %s", url[:70])
            return False

        if is_listing_detail_url(url) and await self.is_in_db(url):
            await self.mark_as_scraped(url)
            logger.info("⏭️ Ya en BD — sin fetch: %s", url[:70])
            return True

        if not self.redis:
            return False

        try:
            key = self._normalize_url_key(url)
            if self.redis.sismember("holanducia:processed_urls", url) or self.redis.sismember(
                "holanducia:processed_urls", key
            ):
                prop = await self.connector.get_property_by_url(url)
                if not prop:
                    logger.info("Redis obsoleto (sin BD) — re-scrape: %s", url[:70])
                    return False
                return True
            return False
        except Exception as e:
            logger.warning(f"Could not check Redis for duplicates: {e}")
            return False

    async def mark_as_scraped(self, url: str):
        """Marca URL procesada; no cachea páginas índice."""
        if is_portal_index_url(url):
            return
        if not self.redis:
            return

        try:
            key = self._normalize_url_key(url)
            self.redis.sadd("holanducia:processed_urls", url)
            if key != url:
                self.redis.sadd("holanducia:processed_urls", key)
        except Exception as e:
            logger.warning(f"Could not save URL to Redis: {e}")

    async def scrape_with_crawl4ai(self, url: str, schema: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        skip_cache = is_portal_index_url(url) or await self._needs_portal_rescrape(url)
        if not skip_cache and await self.is_already_scraped(url):
            logger.info("⏭️ Omitiendo fetch — ya procesado: %s", url[:70])
            return None

        if schema:
            logger.info(f"🕷️ Crawl4AI Scan (schema): {url}")
            try:
                from scrapers.crawl4ai_client import Crawl4AIClient

                client = Crawl4AIClient()
                return await client.scrape_with_schema(url, schema)
            except Exception as e:
                logger.warning(f"Crawl4AI schema scan failed for {url}: {e}")
                return None

        logger.info(f"🕷️ Portal fetch: {url}")
        try:
            from scrapers.portal_fetcher import fetch_portal_page

            return await fetch_portal_page(url, crawl4ai_fetch=self._crawl4ai_page_raw)
        except Exception as e:
            logger.warning(f"Portal fetch failed for {url}: {e}")
            return None

    async def _crawl4ai_page_raw(self, url: str) -> Optional[Dict[str, Any]]:
        from scrapers.crawl4ai_client import Crawl4AIClient

        return await Crawl4AIClient().scrape_page(url)

    async def scrape_with_firecrawl(self, url: str, schema: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        skip_cache = is_portal_index_url(url) or await self._needs_portal_rescrape(url)
        if not skip_cache and await self.is_already_scraped(url):
            logger.info("⏭️ Omitiendo fetch — ya procesado: %s", url[:70])
            return None

        logger.info(f"🔥 Deep Intelligence Scan (Spending Credit): {url}")
        headers = {
            "Authorization": f"Bearer {self.firecrawl_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "url": url,
            "formats": ["json"] if schema else ["markdown"]
        }
        
        if schema:
            payload["jsonOptions"] = {"schema": schema}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.firecrawl_base}/scrape", json=payload, headers=headers)
                if response.status_code != 200:
                    return None
                data = response.json()
                return data.get("data", {})
        except Exception as e:
            logger.warning(f"Scan failed for {url}: {e}")
            return None

    async def save_results(self):
        if not self.results:
            return

        logger.info(f"💾 Saving {len(self.results)} verified leads to HolanducIA")
        for prop in self.results:
            try:
                # 1. Opportunity Analysis
                market_avg = 3200.0 
                analysis = await self.connector.analyze_property(prop, market_avg)
                prop['opportunity_score'] = analysis.get('score', 50)
                
                # 2. Persistence
                await self.connector.upsert_property(prop)
                
                # 3. MARK AS SCRAPED (Credit saved for next time!)
                await self.mark_as_scraped(prop['url'])
                
                logger.info(f"✅ Saved & Cached: {prop['url']}")
            except Exception as e:
                logger.error(f"Failed to persist lead: {e}")

