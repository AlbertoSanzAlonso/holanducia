import os
import httpx
import logging
from scrapers.base_scraper import BaseScraper
from scrapers.agency.analyst import AnalystAgent

logger = logging.getLogger(__name__)

class FirecrawlSniper(BaseScraper):
    def __init__(self, limit=50):
        super().__init__("Firecrawl-Sniper")
        self.api_key = os.getenv("FIRECRAWL_API_KEY")
        self.api_url = "https://api.firecrawl.dev/v1/scrape"
        self.limit = limit
        self.analyst = AnalystAgent()

    async def scrape_portals(self, urls: list):
        """Ejecuta el modo ahorro sobre una lista de URLs de portales"""
        if not self.api_key:
            logger.error("🚫 No hay FIRECRAWL_API_KEY configurada. Misión Sniper abortada.")
            return 0
            
        total_leads = 0
        
        for url in urls:
            if total_leads >= self.limit: break
            
            logger.info(f"🎯 Sniper apuntando a: {url}")
            
            try:
                # 1. SCRAPE QUIRÚRGICO (1 solo crédito de Firecrawl)
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        self.api_url,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={
                            "url": url,
                            "formats": ["markdown"],
                            "onlyMainContent": True
                        }
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"❌ Error en Firecrawl ({response.status_code}): {response.text}")
                        continue
                        
                    raw_data = response.json()
                    markdown_content = raw_data.get("data", {}).get("markdown", "")
                    
                    if not markdown_content:
                        logger.warning("⚠️ Firecrawl devolvió contenido vacío.")
                        continue
                        
                    # 2. EXTRACCIÓN MASIVA AI (1 sola llamada a OpenAI para 30+ leads)
                    # Deduct the domain from URL for source naming
                    source_name = url.split("//")[-1].split("/")[0].replace("www.", "")
                    leads = await self.analyst.parse_bulk_text(markdown_content, source_name)
                    
                    # 3. INYECCIÓN EN BASE DE DATOS
                    for lead in leads:
                        if total_leads >= self.limit: break
                        
                        success = await self.connector.upsert_property(lead)
                        if success:
                            total_leads += 1
                            logger.info(f"✨ Sniper impactó: {lead['title']} en {lead.get('city','Málaga')}")
                            
            except Exception as e:
                logger.error(f"❌ Error en misión Sniper: {e}")
                
        return total_leads
