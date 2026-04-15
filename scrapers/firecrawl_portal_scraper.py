import asyncio
import logging
import httpx
from typing import List, Dict, Any, Optional
from scrapers.base_scraper import BaseScraper, DEEP_PROPERTY_SCHEMA

logger = logging.getLogger(__name__)

class FirecrawlPortalScraper(BaseScraper):
    def __init__(self, portal_name: str, search_query: str, city: str = "madrid"):
        super().__init__(source_name=portal_name, base_url="", settings={"city": city})
        self.search_query = search_query
        self.city = city
        self.portal_name = portal_name

    async def scrape(self):
        logger.info(f"🚀 Mass Scraping {self.portal_name} for '{self.search_query}' in {self.city}")
        
        # 1. Search for listing URLs using Firecrawl
        listing_urls = await self._discover_listing_urls()
        
        if not listing_urls:
            logger.warning(f"No listings found for {self.portal_name}")
            return

        # 1.1. FILTRO DE CRÉDITOS: Solo scrapeamos lo que no conocemos
        new_urls = []
        for url in listing_urls:
            if not await self.is_already_scraped(url):
                new_urls.append(url)
        
        if not new_urls:
            logger.info("✨ Todo está al día. No hay nuevos leads que scrapear (Ahorraste créditos).")
            return

        logger.info(f"🔍 Found {len(new_urls)} NEW leads (Skipped {len(listing_urls) - len(new_urls)} duplicates). Starting extraction...")

        # 2. Scrape each NEW URL in parallel
        semaphore = asyncio.Semaphore(5)
        
        tasks = []
        for url in new_urls[:50]: # Limit for safety
            tasks.append(self._scrape_single_listing(url, semaphore))
        
        results = await asyncio.gather(*tasks)
        self.results = [r for r in results if r]
        
        logger.info(f"✅ Mass scraping completed. {len(self.results)} new leads ready for DB.")


    async def _discover_listing_urls(self) -> List[str]:
        """Uses Firecrawl /search to find listing URLs from the portal"""
        search_prompt = f"site:{self.portal_name.lower()}.com venta piso {self.search_query} {self.city}"
        
        headers = {
            "Authorization": f"Bearer {self.firecrawl_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": search_prompt,
            "limit": 20 # Search results for discovery
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post("https://api.firecrawl.dev/v1/search", json=payload, headers=headers)
                if response.status_code != 200:
                    logger.error(f"Firecrawl Search Error: {response.text}")
                    return []
                
                data = response.json()
                urls = [item.get("url") for item in data.get("data", []) if item.get("url")]
                # Filter to only keep listing pages (pattern matches portal)
                # This is a heuristic, can be improved per portal
                return [u for u in urls if "/vivienda/" in u or "/inmueble/" in u or "/anuncio/" in u]
        except Exception as e:
            logger.error(f"Discovery phase failed: {e}")
            return []

    async def _scrape_single_listing(self, url: str, semaphore: asyncio.Semaphore) -> Optional[Dict[str, Any]]:
        async with semaphore:
            data = await self.scrape_with_firecrawl(url, DEEP_PROPERTY_SCHEMA)
            if not data:
                return None
            
            # Post-process and ensure fields
            property_data = {
                "external_id": url.split("/")[-1].split(".")[0], # Simple heuristic
                "source": self.portal_name,
                "url": url,
                "title": data.get("title"),
                "price": data.get("price", 0),
                "city": data.get("city", self.city),
                "neighborhood": data.get("neighborhood"),
                "address": data.get("address"),
                "rooms": data.get("rooms"),
                "bathrooms": data.get("bathrooms"),
                "size_m2": data.get("size_m2"),
                "has_parking": data.get("has_parking", False),
                "has_terrace": data.get("has_terrace", False),
                "has_pool": data.get("has_pool", False),
                "description": data.get("description"),
                "images": data.get("images", []),
                "is_individual": data.get("is_individual", False),
                "is_agency": not data.get("is_individual", True)
            }
            
            return property_data
