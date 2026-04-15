import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import httpx
import logging
import os
import sys
import redis

# Ensure shared directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared.insforge_connector import InsForgeConnector

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
        
        # InsForge Connector
        self.connector = InsForgeConnector(
            oss_host=os.getenv("INSFORGE_URL"),
            api_key=os.getenv("INSFORGE_ANON_KEY")
        )

        # Redis Deduplication Layer
        redis_host = os.getenv("REDIS_HOST", "redis") # "redis" because of docker-compose
        try:
            self.redis = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)
            logger.info(f"✅ Redis Deduplication active for {self.source_name}")
        except Exception as e:
            self.redis = None
            logger.warning(f"❌ Redis not available, deduplication disabled: {e}")

    @abstractmethod
    async def scrape(self):
        pass

    async def is_already_scraped(self, url: str) -> bool:
        """Checks if URL was already processed in the last 7 days"""
        if not self.redis:
            return False
        
        try:
            # We use a Set in Redis for global uniqueness
            return self.redis.sismember("holanducia:processed_urls", url)
        except Exception as e:
            logger.warning(f"Could not check Redis for duplicates: {e}")
            return False

    async def mark_as_scraped(self, url: str):
        """Marks URL as processed to avoid re-scraping and wasting Firecrawl credits"""
        if not self.redis:
            return
            
        try:
            self.redis.sadd("holanducia:processed_urls", url)
        except Exception as e:
            logger.warning(f"Could not save URL to Redis: {e}")

    async def scrape_with_firecrawl(self, url: str, schema: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        # Check before spending credits!
        if await self.is_already_scraped(url):
            logger.info(f"⏭️ Skipping (Already in Redis): {url}")
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

