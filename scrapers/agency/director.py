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
        
        # Parámetros de la misión
        quota = request.get("target_leads", 10) if request else settings.get("target_leads", 10)
        fb_groups = request.get("groups", []) if request else settings.get("facebook_groups", [])
        
        if not fb_groups:
            logger.warning("🚫 No hay grupos de Facebook configurados para la misión.")
            return

        logger.info(f"🕵️‍♂️ Iniciando Misión de Captación Masiva. Objetivo: {quota} leads nuevos.")
        
        # 1. Ejecución Secuencial para máxima estabilidad
        scraper = FacebookScraper(fb_groups[0], limit=quota)
        results = await scraper.scrape_multiple(fb_groups)
        
        logger.info(f"📊 Misión terminada. Procesando {len(results)} candidatos potenciales...")
        
        # El rascador ya se encarga de inyectar, aquí solo hacemos resumen final
        logger.info(f"🏁 Director: Misión cerrada.")
        return results
