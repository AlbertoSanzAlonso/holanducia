import asyncio
import logging
import os
from typing import Any, Dict, List

from scrapers.agency.hunter import HunterAgent
from scrapers.db_connector import DatabaseConnector, build_portal_urls
from scrapers.facebook_scraper import FacebookScraper
from scrapers.portal_utils import portal_host, prioritize_portal_urls, interleave_portal_urls
from scrapers.sync_context import SyncSession, mass_fb_scroll_steps, mass_mode, sync_mode, sync_session

logger = logging.getLogger(__name__)

PORTAL_NAMES = ("Fotocasa", "Habitaclia", "Pisos.com", "Pisos")
MASS_MISSION_TYPES = frozenset({"mass_scrape", "daily_sync"})


def _enabled_portals(settings: Dict[str, Any]) -> List[str]:
    return [
        p.strip().lower()
        for p in (settings.get("portals") or "").split(",")
        if p.strip()
    ]


def _facebook_enabled(settings: Dict[str, Any]) -> bool:
    return "facebook" in _enabled_portals(settings)


def _resolve_fb_groups(settings: Dict[str, Any], res: Dict[str, Any]) -> List[str]:
    """Grupos FB solo si Facebook está activo en fuentes o vienen explícitos en la petición."""
    if res.get("groups") is not None:
        groups = res["groups"]
        if isinstance(groups, str):
            return [g.strip() for g in groups.split(",") if g.strip()] if "," in groups else ([groups.strip()] if groups.strip() else [])
        if isinstance(groups, list):
            return [str(g).strip() for g in groups if str(g).strip()]
        return [str(groups)] if groups else []

    if not _facebook_enabled(settings):
        return []

    raw = settings.get("facebook_groups") or settings.get("groups")
    if isinstance(raw, str):
        return [g.strip() for g in raw.split(",") if g.strip()] if "," in raw else ([raw.strip()] if raw.strip() else [])
    if isinstance(raw, list):
        return [str(g).strip() for g in raw if str(g).strip()]
    return [str(raw)] if raw else []


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

    def _collect_sources(self, fb_groups: list, portal_urls: list) -> List[str]:
        sources: List[str] = []
        if fb_groups:
            sources.append("Facebook")
        for url in portal_urls:
            host = portal_host(url)
            if host != "unknown" and host not in sources:
                sources.append(host)
        return sources

    def _is_mass_mission(self, request: Dict[str, Any]) -> bool:
        return request.get("source_name") in MASS_MISSION_TYPES

    async def execute_mission(self, request: Dict[str, Any] = None):
        settings = await self.db.get_settings() or {}
        res = request or {}
        is_mass = self._is_mass_mission(res)

        if is_mass:
            quota = (
                res.get("target_leads")
                or settings.get("mass_scrape_target")
                or int(os.getenv("MASS_SCRAPE_TARGET", "500"))
            )
            fb_scroll = (
                settings.get("mass_fb_scroll_steps")
                or int(os.getenv("MASS_FB_SCROLL_STEPS", "100"))
            )
        else:
            quota = (
                res.get("target_leads")
                or settings.get("target_leads")
                or settings.get("max_leads_per_portal")
                or 10
            )
            fb_scroll = int(os.getenv("FB_SCROLL_STEPS", "55"))

        fb_groups = _resolve_fb_groups(settings, res)
        portal_urls = res.get("portal_urls") or build_portal_urls(settings)

        if isinstance(portal_urls, str):
            portal_urls = [u.strip() for u in portal_urls.split(",") if u.strip()]

        if not fb_groups and not portal_urls:
            if _facebook_enabled(settings):
                fb_groups = ["41757906864", "1018337428507491", "397742921612774"]
                logger.info("Usando grupos por defecto del escuadron.")
            else:
                logger.warning("Misión sin fuentes — activa portales en Configuración.")

        discovered = await self._discover_listing_urls(settings)
        index_urls = build_portal_urls(settings)
        portal_urls = list(dict.fromkeys(index_urls + portal_urls + discovered))
        if discovered or index_urls:
            logger.info(
                "Director: %s urls de portales (%s índice, %s Hunter)",
                len(portal_urls),
                len(index_urls),
                len(discovered),
            )

        portal_urls = interleave_portal_urls(prioritize_portal_urls(portal_urls))
        sources = self._collect_sources(fb_groups, portal_urls)

        session: SyncSession | None = None
        if is_mass:
            sync_mode.set(True)
            mass_mode.set(True)
            mass_fb_scroll_steps.set(fb_scroll)
            sync_run_id = await self.db.start_sync_run(sources)
            session = SyncSession(sync_run_id, sources)
            sync_session.set(session)
            logger.info(
                "Scraping MASIVO #%s — %s fuentes, cuota %s, scroll FB %s pasos",
                sync_run_id,
                len(sources),
                quota,
                fb_scroll,
            )

        logger.info(
            "Misión%s — cuota %s, %s grupos FB, %s portales",
            " MASIVA" if is_mass else "",
            quota,
            len(fb_groups),
            len(portal_urls),
        )

        total_captured = 0
        attempts = 0
        zero_rounds = 0
        max_attempts = 10 if is_mass else 5

        try:
            while total_captured < quota and attempts < max_attempts:
                attempts += 1
                if attempts > 1:
                    logger.info("Ronda %s — %s/%s procesados", attempts, total_captured, quota)
                    await asyncio.sleep(30 if is_mass else 60)

                round_start = total_captured

                if portal_urls and total_captured < quota:
                    backend = os.getenv("SNIPER_BACKEND", "crawl4ai").lower()
                    logger.info("Sniper (%s) — %s portales", backend, len(portal_urls))

                    if backend == "firecrawl":
                        from scrapers.firecrawl_sniper import FirecrawlSniper

                        sniper = FirecrawlSniper(limit=(quota - total_captured))
                    else:
                        from scrapers.crawl4ai_sniper import Crawl4AISniper

                        sniper = Crawl4AISniper(limit=(quota - total_captured))

                    total_captured += await sniper.scrape_portals(portal_urls)

                if fb_groups and total_captured < quota:
                    import random

                    random.shuffle(fb_groups)
                    scraper = FacebookScraper(fb_groups[0], limit=(quota - total_captured))
                    total_captured += await scraper.scrape_multiple(fb_groups)

                if total_captured >= quota:
                    break

                if total_captured == round_start:
                    zero_rounds += 1
                    if zero_rounds >= 2:
                        logger.warning(
                            "2 rondas consecutivas sin leads nuevos (%s/%s) — abortando misión",
                            total_captured,
                            quota,
                        )
                        break
                else:
                    zero_rounds = 0
        finally:
            if session:
                # mass_scrape acumula oportunidades; solo daily_sync reconcilia bajas
                reconcile = res.get("source_name") == "daily_sync"
                result = await self.db.finalize_sync_run(
                    session.sync_run_id,
                    seen_urls=list(session.seen_urls),
                    sources=session.sources,
                    stats=session.stats,
                    deactivate_missing=reconcile,
                )
                logger.info(
                    "Scraping masivo completado — creados=%s actualizados=%s sin_cambios=%s bajas=%s",
                    session.stats.get("created", 0),
                    session.stats.get("updated", 0),
                    session.stats.get("unchanged", 0),
                    result.get("deactivated", 0),
                )
                sync_mode.set(False)
                mass_mode.set(False)
                sync_session.set(None)

        logger.info("Director: misión cerrada — %s anuncios procesados", total_captured)
        return total_captured
