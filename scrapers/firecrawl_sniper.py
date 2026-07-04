import logging
import os

import httpx

from scrapers.agency.analyst import AnalystAgent
from scrapers.agency.graphs.property_pipeline import run_structured_leads_pipeline
from scrapers.base_scraper import BaseScraper
from scrapers.image_utils import extract_image_urls
from scrapers.portal_sniper_core import (
    build_detail_url_queue,
    scrape_detail_urls_parallel,
)

logger = logging.getLogger(__name__)


class FirecrawlSniper(BaseScraper):
    def __init__(self, limit=50):
        super().__init__("Firecrawl-Sniper", "portals")
        self.api_key = os.getenv("FIRECRAWL_API_KEY")
        self.api_url = "https://api.firecrawl.dev/v1/scrape"
        self.limit = limit
        self.analyst = AnalystAgent()

    async def scrape(self):
        return 0

    async def _fetch_firecrawl(self, url: str) -> dict | None:
        if not self.api_key:
            return None
        if await self.is_already_scraped(url):
            return None

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"url": url, "formats": ["markdown", "html"], "onlyMainContent": True},
                )
                if response.status_code != 200:
                    logger.error("Firecrawl (%s): %s", response.status_code, response.text[:200])
                    return None
                payload = response.json().get("data", {})
                markdown = payload.get("markdown") or ""
                html = payload.get("html") or ""
                return {
                    "markdown": markdown,
                    "html": html,
                    "images": extract_image_urls(html=html, markdown=markdown),
                }
        except Exception as e:
            logger.warning("Firecrawl falló en %s: %s", url[:60], e)
            return None

    async def scrape_portals(self, urls: list):
        if not self.api_key:
            logger.error("No hay FIRECRAWL_API_KEY configurada. Misión Sniper abortada.")
            return 0
        if not urls:
            return 0

        to_scrape = await build_detail_url_queue(urls, self._fetch_firecrawl, self.limit)
        if not to_scrape:
            return 0

        logger.info("Sniper Firecrawl: extracción profunda de %s fichas", len(to_scrape))

        bulk_leads = await scrape_detail_urls_parallel(
            to_scrape,
            fetch_page=self._fetch_firecrawl,
            analyst=self.analyst,
            should_skip=self.is_already_scraped,
        )

        if not bulk_leads:
            return 0

        source_name = bulk_leads[0].get("source") or "portals"
        result = await run_structured_leads_pipeline(
            source=source_name,
            base_url=to_scrape[0],
            leads=bulk_leads,
            limit=self.limit,
            connector=self.connector,
            persist_lead=self._persist_lead,
            is_already_scraped=self.is_already_scraped,
            mark_as_scraped=self.mark_as_scraped,
        )
        return result.get("saved_count", 0)

    async def _persist_lead(self, ai_data: dict, _base_url: str) -> bool:
        try:
            await self.connector.upsert_property_with_embedding(ai_data)
            return True
        except Exception as e:
            logger.error("No se pudo guardar lead: %s", e)
            return False
