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
        
        # Si sigue sin haber nada, usamos tus grupos habituales para que no se pare
        if not fb_groups:
            fb_groups = ['41757906864', '1018337428507491', '397742921612774']
            logger.info("ℹ️ Usando grupos por defecto del escuadrón.")
        
        # Normalizamos a lista (Evitando el bug de recorrer letras una a una)
        if isinstance(fb_groups, str):
            if "," in fb_groups:
                fb_groups = [g.strip() for g in fb_groups.split(",")]
            else:
                fb_groups = [fb_groups.strip()]
        elif not isinstance(fb_groups, list):
            fb_groups = [str(fb_groups)]

        logger.info(f"🕵️‍♂️ Iniciando Misión de Captación Masiva. Objetivo: {quota} leads nuevos.")
        
        total_captured = 0
        attempts = 0
        max_attempts = 5 # Para no entrar en bucle infinito si no hay nada en todo el día
        
        while total_captured < quota and attempts < max_attempts:
            attempts += 1
            if attempts > 1:
                logger.info(f"⏳ Objetivo no alcanzado ({total_captured}/{quota}). Reintentando ronda {attempts}/{max_attempts}...")
                await asyncio.sleep(60) # Espera táctica entre rondas
                
            # Rotación Inteligente
            import random
            random.shuffle(fb_groups)
            
            # 1. Ejecución Secuencial para máxima estabilidad
            scraper = FacebookScraper(fb_groups[0], limit=(quota - total_captured))
            new_leads = await scraper.scrape_multiple(fb_groups)
            total_captured += new_leads
            
            if total_captured >= quota:
                logger.info(f"🎯 ¡OBJETIVO CUMPLIDO! Se han captado {total_captured} leads.")
                break

        logger.info(f"🏁 Director: Misión cerrada con {total_captured} leads totales.")
        return total_captured
