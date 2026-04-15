import asyncio
import logging
import os
from typing import List, Dict, Any
from scrapers.facebook_scraper import FacebookScraper
from scrapers.insforge_connector import InsForgeConnector

logger = logging.getLogger(__name__)

class DirectorAgent:
    def __init__(self):
        self.insforge = InsForgeConnector()
        self.max_parallel_groups = 3 # Límite para no saturar la RAM
        
    async def execute_mission(self, quota: int = 10):
        """Coordina múltiples agentes para alcanzar la cuota de leads requerida"""
        logger.info(f"🕵️‍♂️ Iniciando Misión de Captación Masiva. Objetivo: {quota} leads nuevos.")
        
        # 1. Obtenemos configuración (Grupos de Facebook autorizados)
        settings = await self.insforge.get_settings()
        fb_groups = settings.get("facebook_groups", []) if settings else []
        
        if not fb_groups:
            logger.warning("⚠️ No hay grupos de Facebook configurados. Misión abortada.")
            return

        total_verified_leads = 0
        all_results = []
        
        # 2. Bucle de Persistencia: Vamos lanzando grupos en paralelo hasta llenar la cuota
        # Procesamos en 'chunks' de max_parallel_groups
        for i in range(0, len(fb_groups), self.max_parallel_groups):
            if total_verified_leads >= quota: break
            
            chunk = fb_groups[i : i + self.max_parallel_groups]
            logger.info(f"🚀 Lanzando escuadrón sobre {len(chunk)} grupos: {chunk}")
            
            # Lanzamos los rascadores en paralelo
            tasks = [self._scrape_and_verify(group_url, quota - total_verified_leads) for group_url in chunk]
            chunk_results = await asyncio.gather(*tasks)
            
            # Recolectamos y sumamos
            for leads in chunk_results:
                if leads:
                    total_verified_leads += len(leads)
                    all_results.extend(leads)
            
            logger.info(f"📊 Estado de la misión: {total_verified_leads}/{quota} leads validados.")
            
            if total_verified_leads >= quota:
                logger.info("🎯 ¡Cuota alcanzada! Deteniendo infiltración masiva.")
                break

        logger.info(f"🏁 Misión Finalizada. {total_verified_leads} leads totales inyectados en el sistema.")
        return all_results

    async def _scrape_and_verify(self, group_url: str, remaining_quota: int) -> List[Dict[str, Any]]:
        """Tarea individual de rascado y validación"""
        try:
            # Calculamos un límite proporcional para este grupo
            # Si nos faltan 5, le pedimos 50 brutos para asegurar
            fetch_limit = max(50, remaining_quota * 10)
            
            scraper = FacebookScraper(group_url, limit=fetch_limit)
            leads = await scraper.scrape()
            
            if not leads:
                return []
                
            # Guardamos en la DB (Deduplicación semántica ya integrada en el scraper)
            saved_count = 0
            for lead in leads:
                success = await self.insforge.upsert_property(lead)
                if success: saved_count += 1
                
            logger.info(f"✅ Grupo {group_url}: {saved_count} nuevos leads inyectados.")
            return leads[:saved_count] if saved_count > 0 else []
            
        except Exception as e:
            logger.error(f"❌ Error crítico en grupo {group_url}: {e}")
            return []
