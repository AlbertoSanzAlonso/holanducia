import logging
import os

from scrapers.agency.analyst import AnalystAgent
from scrapers.agency.graphs.property_pipeline import run_structured_leads_pipeline
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class Crawl4AISniper(BaseScraper):
    def __init__(self, limit=50):
        super().__init__("Crawl4AI-Sniper", "portals")
        self.limit = limit
        self.analyst = AnalystAgent()

    async def scrape(self):
        return []

    async def scrape_portals(self, urls: list):
        """Scrapea portales con Crawl4AI + pipeline agéntico (Curator → Analyst → Persist)."""
        if not (os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")):
            logger.error("No hay OPENAI_API_KEY ni GROQ_API_KEY configurada. Misión Sniper abortada.")
            return 0

        total_leads = 0

        for url in urls:
            if total_leads >= self.limit:
                break

            logger.info("Sniper Crawl4AI apuntando a: %s", url)

            try:
                data = await self.scrape_with_crawl4ai(url)
                markdown_content = (data or {}).get("markdown", "")

                if not markdown_content:
                    logger.warning("Crawl4AI devolvió contenido vacío.")
                    continue

                source_name = url.split("//")[-1].split("/")[0].replace("www.", "")
                bulk_leads = await self.analyst.parse_bulk_text(markdown_content, source_name)

                remaining = self.limit - total_leads
                result = await run_structured_leads_pipeline(
                    source=source_name,
                    base_url=url,
                    leads=bulk_leads,
                    limit=remaining,
                    connector=self.connector,
                    persist_lead=self._persist_lead,
                    is_already_scraped=self.is_already_scraped,
                    mark_as_scraped=self.mark_as_scraped,
                )

                saved = result.get("saved_count", 0)
                total_leads += saved
                stats = result.get("stats", {})
                logger.info(
                    "Portal %s: %s guardados (%s duplicados, %s analizados)",
                    url,
                    saved,
                    stats.get("duplicates", 0),
                    stats.get("analyzed", 0),
                )

            except Exception as e:
                logger.error("Error en misión Sniper Crawl4AI: %s", e)

        return total_leads

    async def _persist_lead(self, ai_data: dict, _base_url: str) -> bool:
        try:
            await self.connector.upsert_property(ai_data)
            return True
        except Exception as e:
            logger.error("No se pudo guardar lead: %s", e)
            return False
