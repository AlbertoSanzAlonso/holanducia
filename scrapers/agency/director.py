import asyncio
import logging
import os
from typing import Any, Dict, List

from scrapers.agency.hunter import HunterAgent
from scrapers.db_connector import DatabaseConnector, build_portal_urls
from scrapers.facebook_scraper import FacebookScraper
from scrapers.portal_utils import prioritize_portal_urls

logger = logging.getLogger(__name__)

PORTAL_NAMES = ("Fotocasa", "Habitaclia", "Pisos.com", "Pisos")


class DirectorAgent:
    def __init__(self, api_url: str = None):
        self.db = DatabaseConnector(api_url=api_url)
        self.hunter = HunterAgent()

    async def _discover_listing_urls(self, settings: Dict[str, Any]) -> List[str]:
        cities = settings.get("cities") or ["malaga"]
        portals_raw = settings.get("portals") or ""
        portals = [
            p.strip()
            for p in portals_raw.split(",")
            if p.strip() and p.strip().lower() not in {"facebook", "catastro"}
        ]

        discovered: List[str] = []
        for city in cities:
            city_slug = city.strip().lower().replace(" ", "-")
            for portal in portals:
                portal_key = next((name for name in PORTAL_NAMES if name.lower() in portal.lower()), portal)
                try:
                    urls = await self.hunter.discover(portal_key, city_slug)
                    discovered.extend(urls)
                    logger.info("Hunter: %s urls en %s (%s)", len(urls), portal_key, city_slug)
                except Exception as e:
                    logger.error("Hunter falló en %s/%s: %s", portal_key, city_slug, e)

        return list(dict.fromkeys(discovered))

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

        discovered = await self._discover_listing_urls(settings)
        if discovered:
            portal_urls = list(dict.fromkeys(portal_urls + discovered))
            logger.info("Director: %s urls de portales (listados + Hunter)", len(portal_urls))

        portal_urls = prioritize_portal_urls(portal_urls)

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
