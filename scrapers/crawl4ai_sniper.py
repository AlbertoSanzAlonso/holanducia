import logging
import os

from scrapers.agency.analyst import AnalystAgent
from scrapers.agency.graphs.property_pipeline import run_structured_leads_pipeline
from scrapers.base_scraper import BaseScraper
from scrapers.portal_sniper_core import (
    build_detail_url_queue,
    scrape_detail_urls_parallel,
)

logger = logging.getLogger(__name__)


class Crawl4AISniper(BaseScraper):
    def __init__(self, limit=50):
        super().__init__("Crawl4AI-Sniper", "portals")
        self.limit = limit
        self.analyst = AnalystAgent()

    async def scrape(self):
        return []

    async def scrape_portals(self, urls: list):
        """Índice → fichas individuales → parser + Analyst → persist."""
        if not (os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")):
            logger.error("No hay OPENAI_API_KEY ni GROQ_API_KEY configurada. Misión Sniper abortada.")
            return 0

        if not urls:
            return 0

        to_scrape = await build_detail_url_queue(urls, self.scrape_with_crawl4ai, self.limit)
        if not to_scrape:
            return 0

        logger.info("Sniper Crawl4AI: extracción profunda de %s fichas (cuota %s)", len(to_scrape), self.limit)

        bulk_leads = await scrape_detail_urls_parallel(
            to_scrape,
            fetch_page=self.scrape_with_crawl4ai,
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

        saved = result.get("saved_count", 0)
        stats = result.get("stats", {})
        logger.info(
            "Portal %s: %s guardados (%s actualizados, %s rechazados)",
            source_name,
            saved,
            stats.get("updated", 0),
            stats.get("rejected_supervisor", 0),
        )
        return saved

    async def _persist_lead(self, ai_data: dict, _base_url: str) -> bool:
        try:
            await self.connector.upsert_property_with_embedding(ai_data)
            return True
        except Exception as e:
            logger.error("No se pudo guardar lead: %s", e)
            return False
