import asyncio
import logging
from typing import List, Dict, Any
from scrapers.insforge_connector import InsForgeConnector
from scrapers.facebook_scraper import FacebookScraper

logger = logging.getLogger(__name__)

class DirectorAgent:
    def __init__(self):
        self.insforge = InsForgeConnector()

    async def execute_mission(self, request: Dict[str, Any] = None):
        """Coordinación total de la misión de captación"""
        settings = await self.insforge.get_settings()
        
        # Parámetros de la misión con Fallback de seguridad
        res = request or {}
        quota = res.get("target_leads") or settings.get("target_leads") or 10
        fb_groups = res.get("groups") or settings.get("facebook_groups") or settings.get("groups")
        portal_urls = res.get("portal_urls") or settings.get("portal_urls") or []
        
        # Normalizamos portal_urls a lista
        if isinstance(portal_urls, str):
            portal_urls = [u.strip() for u in portal_urls.split(",") if u.strip()]

        # Si sigue sin haber nada de nada, usamos tus grupos habituales
        if not fb_groups and not portal_urls:
            fb_groups = ['41757906864', '1018337428507491', '397742921612774']
            logger.info("ℹ️ Usando grupos por defecto del escuadrón.")
        
        # ... (Saneamiento de fb_groups igual que antes) ...
        if isinstance(fb_groups, str):
            if "," in fb_groups: fb_groups = [g.strip() for g in fb_groups.split(",")]
            else: fb_groups = [fb_groups.strip()]
        elif not isinstance(fb_groups, list): fb_groups = [str(fb_groups)] if fb_groups else []

        logger.info(f"🕵️‍♂️ Iniciando Misión. Objetivo: {quota} leads. Fuentes: {len(fb_groups)} grupos FB, {len(portal_urls)} portales Sniper.")
        
        total_captured = 0
        attempts = 0
        max_attempts = 5
        
        while total_captured < quota and attempts < max_attempts:
            attempts += 1
            if attempts > 1:
                logger.info(f"⏳ Objetivo no alcanzado ({total_captured}/{quota}). Pasando siguiente ronda...")
                await asyncio.sleep(60)

            # 1. MOTOR FACEBOOK (Escuadrón)
            if fb_groups:
                import random
                random.shuffle(fb_groups)
                scraper = FacebookScraper(fb_groups[0], limit=(quota - total_captured))
                total_captured += await scraper.scrape_multiple(fb_groups)

            # 2. MOTOR PORTALES (Sniper via Firecrawl)
            if portal_urls and total_captured < quota:
                logger.info(f"🎯 Activando Modo Francotirador sobre {len(portal_urls)} portales...")
                from scrapers.firecrawl_sniper import FirecrawlSniper
                sniper = FirecrawlSniper(limit=(quota - total_captured))
                total_captured += await sniper.scrape_portals(portal_urls)
            
            if total_captured >= quota: break

        logger.info(f"🏁 Director: Misión cerrada con {total_captured} leads totales.")
        return total_captured
