import asyncio
import logging
import os

from scrapers.agency.analyst import AnalystAgent
from scrapers.agency.graphs.property_pipeline import run_structured_leads_pipeline
from scrapers.base_scraper import BaseScraper
from scrapers.image_utils import is_portal_index_url
from scrapers.portal_detail_parser import is_card_snippet, parse_portal_detail
from scrapers.portal_utils import extract_listing_urls, is_listing_detail_url

logger = logging.getLogger(__name__)

MAX_DETAIL_SCRAPES_PER_INDEX = 25
DETAIL_CONCURRENCY = 3


class Crawl4AISniper(BaseScraper):
    def __init__(self, limit=50):
        super().__init__("Crawl4AI-Sniper", "portals")
        self.limit = limit
        self.analyst = AnalystAgent()

    async def scrape(self):
        return []

    async def _scrape_detail_listing(self, url: str, source_name: str) -> dict | None:
        if await self.is_already_scraped(url):
            logger.info("⏭️ Ficha ya procesada: %s", url)
            return None

        data = await self.scrape_with_crawl4ai(url)
        if not data:
            return None

        markdown = data.get("markdown") or ""
        page_images = data.get("images") or []
        page_html = data.get("html") or ""

        if not markdown.strip():
            return None

        pre_parsed = parse_portal_detail(url, markdown, html=page_html, images=page_images)
        pre_parsed.pop("_parse_meta", None)

        if is_card_snippet(pre_parsed.get("title"), pre_parsed.get("description")):
            logger.warning("Contenido tipo tarjeta en %s — reintentando con IA profunda", url)
            pre_parsed = {"images": page_images[:8], "url": url}

        lead = await self.analyst.parse_portal_detail(
            markdown,
            source_name,
            url=url,
            pre_parsed=pre_parsed,
        )
        if not lead:
            return None

        lead["url"] = url.rstrip("/")
        if page_images and not lead.get("images"):
            lead["images"] = page_images[:8]
        return lead

    async def scrape_portals(self, urls: list):
        """Scrapea portales: índice → URLs de ficha → extracción profunda por anuncio."""
        if not (os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")):
            logger.error("No hay OPENAI_API_KEY ni GROQ_API_KEY configurada. Misión Sniper abortada.")
            return 0

        detail_urls: list[str] = []

        for url in urls:
            if is_portal_index_url(url):
                logger.info("Sniper índice: descubriendo fichas en %s", url)
                data = await self.scrape_with_crawl4ai(url)
                if not data:
                    continue
                listing_urls = extract_listing_urls(
                    data.get("html") or "",
                    data.get("markdown") or "",
                    url,
                )
                logger.info("Fichas detectadas en índice: %s", len(listing_urls))
                detail_urls.extend(listing_urls)
            elif is_listing_detail_url(url):
                detail_urls.append(url)
            else:
                detail_urls.append(url)

        detail_urls = list(dict.fromkeys(detail_urls))
        if not detail_urls:
            return 0

        cap = min(self.limit, MAX_DETAIL_SCRAPES_PER_INDEX, len(detail_urls))
        to_scrape = detail_urls[:cap]

        logger.info("Sniper: extracción profunda de %s fichas", len(to_scrape))

        sem = asyncio.Semaphore(DETAIL_CONCURRENCY)

        async def process_one(detail_url: str):
            async with sem:
                source = detail_url.split("//")[-1].split("/")[0].replace("www.", "")
                return await self._scrape_detail_listing(detail_url, source)

        results = await asyncio.gather(*[process_one(u) for u in to_scrape])
        bulk_leads = [lead for lead in results if lead]

        if not bulk_leads:
            return 0

        base_url = to_scrape[0] if to_scrape else (urls[0] if urls else "")
        source_name = base_url.split("//")[-1].split("/")[0].replace("www.", "")

        result = await run_structured_leads_pipeline(
            source=source_name,
            base_url=base_url,
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
