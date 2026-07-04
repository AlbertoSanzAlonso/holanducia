import logging
import os

from scrapers.agency.analyst import AnalystAgent
from scrapers.base_scraper import BaseScraper
from scrapers.portal_sniper_core import (
    build_detail_url_queue,
    scrape_and_persist_details,
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
        """Índice → ficha → guardar en BD al instante (streaming)."""
        if not (os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")):
            logger.error("No hay OPENAI_API_KEY ni GROQ_API_KEY configurada. Misión Sniper abortada.")
            return 0

        if not urls:
            return 0

        to_scrape = await build_detail_url_queue(urls, self.scrape_with_crawl4ai, self.limit)
        if not to_scrape:
            return 0

        logger.info(
            "Sniper Crawl4AI: %s fichas en cola — guardado incremental (cuota %s)",
            len(to_scrape),
            self.limit,
        )

        async def report_status(status: str, message: str) -> None:
            await self.connector.upsert_scraping_status(status, message)

        saved, stats = await scrape_and_persist_details(
            to_scrape,
            fetch_page=self.scrape_with_crawl4ai,
            analyst=self.analyst,
            should_skip=self.is_already_scraped,
            connector=self.connector,
            mark_as_scraped=self.mark_as_scraped,
            limit=self.limit,
            base_url=to_scrape[0],
            report_status=report_status,
        )

        logger.info(
            "Portal Crawl4AI: %s en BD (%s nuevos, %s actualizados, %s rechazados supervisor)",
            saved,
            stats.get("created", 0),
            stats.get("updated", 0),
            stats.get("rejected_supervisor", 0),
        )
        return saved
