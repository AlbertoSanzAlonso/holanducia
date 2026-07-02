import asyncio
import logging
import os
from typing import Any, Dict, List

from scrapers.db_connector import DatabaseConnector, build_portal_urls
from scrapers.facebook_scraper import FacebookScraper

logger = logging.getLogger(__name__)


class DirectorAgent:
    def __init__(self, api_url: str = None):
        self.db = DatabaseConnector(api_url=api_url)

    async def execute_mission(self, request: Dict[str, Any] = None):
        settings = await self.db.get_settings() or {}

        res = request or {}
        quota = res.get("target_leads") or settings.get("target_leads") or settings.get("max_leads_per_portal") or 10
        fb_groups = res.get("groups") or settings.get("facebook_groups") or settings.get("groups")
        portal_urls = res.get("portal_urls") or build_portal_urls(settings)

        if isinstance(portal_urls, str):
            portal_urls = [u.strip() for u in portal_urls.split(",") if u.strip()]

        if not fb_groups and not portal_urls:
            fb_groups = ["41757906864", "1018337428507491", "397742921612774"]
            logger.info("Usando grupos por defecto del escuadron.")

        if isinstance(fb_groups, str):
            if "," in fb_groups:
                fb_groups = [g.strip() for g in fb_groups.split(",")]
            else:
                fb_groups = [fb_groups.strip()]
        elif not isinstance(fb_groups, list):
            fb_groups = [str(fb_groups)] if fb_groups else []

        logger.info(
            "Iniciando mision. Objetivo: %s leads. Fuentes: %s grupos FB, %s portales Sniper.",
            quota,
            len(fb_groups),
            len(portal_urls),
        )

        total_captured = 0
        attempts = 0
        max_attempts = 5

        while total_captured < quota and attempts < max_attempts:
            attempts += 1
            if attempts > 1:
                logger.info("Objetivo no alcanzado (%s/%s). Pasando siguiente ronda...", total_captured, quota)
                await asyncio.sleep(60)

            if fb_groups:
                import random

                random.shuffle(fb_groups)
                scraper = FacebookScraper(fb_groups[0], limit=(quota - total_captured))
                total_captured += await scraper.scrape_multiple(fb_groups)

            if portal_urls and total_captured < quota:
                backend = os.getenv("SNIPER_BACKEND", "crawl4ai").lower()
                logger.info("Activando Modo Francotirador (%s) sobre %s portales...", backend, len(portal_urls))

                if backend == "firecrawl":
                    from scrapers.firecrawl_sniper import FirecrawlSniper

                    sniper = FirecrawlSniper(limit=(quota - total_captured))
                else:
                    from scrapers.crawl4ai_sniper import Crawl4AISniper

                    sniper = Crawl4AISniper(limit=(quota - total_captured))

                total_captured += await sniper.scrape_portals(portal_urls)

            if total_captured >= quota:
                break

        logger.info("Director: mision cerrada con %s leads totales.", total_captured)
        return total_captured
