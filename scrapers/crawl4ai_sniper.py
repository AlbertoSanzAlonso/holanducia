import hashlib
import logging
import os

from scrapers.agency.analyst import AnalystAgent
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
        """Scrapea portales con Crawl4AI (gratis) + AnalystAgent (OpenAI)."""
        if not (os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")):
            logger.error("🚫 No hay OPENAI_API_KEY ni GROQ_API_KEY configurada. Misión Sniper abortada.")
            return 0

        total_leads = 0

        for url in urls:
            if total_leads >= self.limit:
                break

            logger.info(f"🎯 Sniper Crawl4AI apuntando a: {url}")

            try:
                data = await self.scrape_with_crawl4ai(url)
                markdown_content = (data or {}).get("markdown", "")

                if not markdown_content:
                    logger.warning("⚠️ Crawl4AI devolvió contenido vacío.")
                    continue

                source_name = url.split("//")[-1].split("/")[0].replace("www.", "")
                leads = await self.analyst.parse_bulk_text(markdown_content, source_name)

                for lead in leads:
                    if total_leads >= self.limit:
                        break

                    f_hash = hashlib.md5(f"{lead['title']}{lead['price']}".encode()).hexdigest()[:12]
                    lead["external_id"] = f_hash
                    lead["url"] = f"{url}#sniper-{f_hash}"

                    try:
                        await self.connector.upsert_property(lead)
                        total_leads += 1
                        logger.info(f"✨ Sniper impactó: {lead['title']} en {lead.get('city', 'Málaga')}")
                    except Exception as upsert_error:
                        logger.error(f"❌ No se pudo guardar lead: {upsert_error}")

            except Exception as e:
                logger.error(f"❌ Error en misión Sniper Crawl4AI: {e}")

        return total_leads
