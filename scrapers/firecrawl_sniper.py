import logging
import os

import httpx

from scrapers.agency.analyst import AnalystAgent
from scrapers.agency.graphs.property_pipeline import run_structured_leads_pipeline
from scrapers.base_scraper import BaseScraper
from scrapers.image_utils import extract_image_urls, is_portal_index_url

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

    async def scrape_portals(self, urls: list):
        if not self.api_key:
            logger.error("No hay FIRECRAWL_API_KEY configurada. Misión Sniper abortada.")
            return 0

        total_leads = 0

        for url in urls:
            if total_leads >= self.limit:
                break

            logger.info("Sniper apuntando a: %s", url)

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        self.api_url,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={"url": url, "formats": ["markdown"], "onlyMainContent": True},
                    )

                    if response.status_code != 200:
                        logger.error("Error en Firecrawl (%s): %s", response.status_code, response.text)
                        continue

                    markdown_content = response.json().get("data", {}).get("markdown", "")
                    if not markdown_content:
                        logger.warning("Firecrawl devolvió contenido vacío.")
                        continue

                    source_name = url.split("//")[-1].split("/")[0].replace("www.", "")
                    page_images = extract_image_urls(markdown=markdown_content)

                    if is_portal_index_url(url):
                        bulk_leads = await self.analyst.parse_bulk_text(
                            markdown_content,
                            source_name,
                            page_images=page_images,
                        )
                    else:
                        lead = await self.analyst.parse_raw_text(markdown_content, source_name)
                        bulk_leads = []
                        if lead:
                            if page_images and not lead.get("images"):
                                lead["images"] = page_images[:5]
                            bulk_leads = [lead]

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
                    logger.info("Portal %s: %s leads guardados", url, saved)

            except Exception as e:
                logger.error("Error en misión Sniper: %s", e)

        return total_leads

    async def _persist_lead(self, ai_data: dict, _base_url: str) -> bool:
        try:
            await self.connector.upsert_property(ai_data)
            return True
        except Exception as e:
            logger.error("No se pudo guardar lead: %s", e)
            return False
