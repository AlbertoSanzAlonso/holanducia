import os
import logging
import asyncio
from insforge_connector import InsForgeConnector
from agency.hunter import HunterAgent
from agency.analyst import AnalystAgent

class DirectorAgent:
    def __init__(self):
        self.logger = logging.getLogger("Agency.Director")
        self.connector = InsForgeConnector(
            oss_host=os.getenv("INSFORGE_URL"),
            api_key=os.getenv("INSFORGE_ANON_KEY")
        )
        self.hunter = HunterAgent()
        self.analyst = AnalystAgent()

    async def execute_mission(self, request=None):
        self.logger.info("Starting Mission: AI Intelligence Infiltration")
        
        # CASO 1: Petición específica con URL (ej: Facebook o Idealista puntual)
        if request and request.get('url'):
            url = request['url']
            self.logger.info(f"🎯 Target Acquired: {url}")
            
            if "facebook.com" in url:
                from scrapers.facebook_scraper import FacebookScraper
                try:
                    group_id = url.split("groups/")[1].split("/")[0]
                    scraper = FacebookScraper(group_id)
                    leads = await scraper.scrape()
                    if leads:
                        for lead in leads:
                            cleaned = await self.analyst.parse_raw_text(lead['description'], source="Facebook")
                            if cleaned:
                                cleaned['url'] = lead['url']
                                cleaned['images'] = lead['images']
                                await self.connector.upsert_property(cleaned)
                except Exception as e:
                    self.logger.error(f"Error parsing Facebook URL: {e}")
                return # Misión específica terminada
        
        # CASO 2: Misión General Automática (Basada en Settings)
        settings = await self.connector.get_settings()
        if not settings:
            self.logger.error("No user settings found. Mission Aborted.")
            return

        cities = settings.get("cities") or [""] # Si está vacío, ejecutamos una vez con ciudad vacía
        portals_raw = settings.get("portals")
        portals = [p.strip() for p in portals_raw.split(",")] if portals_raw else ["Facebook"]
        max_leads = settings.get("max_leads_per_portal", 10)
        
        # Filtros opcionales (pueden venir vacíos)
        max_price = settings.get("max_price")
        min_rooms = settings.get("min_rooms")

        self.logger.info(f"Mass Infiltration: {len(portals)} portals. Cities: {cities if cities[0] else 'All'}")

        for city in cities:
            for portal in portals:
                self.logger.info(f"Tasking Hunter with {portal} in {city}")
                
                # Si el portal ya es una URL de Facebook, la usamos directamente
                if "facebook.com/groups/" in portal:
                    urls = [portal]
                else:
                    urls = await self.hunter.discover(portal, city)

                if urls and "facebook.com" in urls[0]:
                    from scrapers.facebook_scraper import FacebookScraper
                    for fb_url in urls:
                        try:
                            # Extraer ID del grupo de forma robusta
                            group_part = fb_url.split("groups/")[1].split("/")[0].split("?")[0]
                            self.logger.info(f"🚀 Infiltrating FB Group: {group_part}")
                            scraper = FacebookScraper(group_part, limit=max_leads)
                            leads = await scraper.scrape()
                            if leads:
                                for lead in leads:
                                    cleaned = await self.analyst.parse_raw_text(lead['description'], source="Facebook")
                                    if cleaned:
                                        cleaned['url'] = lead['url']
                                        cleaned['images'] = lead['images']
                                        await self.connector.upsert_property(cleaned)
                        except Exception as e:
                            self.logger.error(f"Error in FB group scrape ({fb_url}): {e}")
                else:
                    # OTROS PORTALES (Firecrawl)
                    if urls:
                        self.logger.info(f"Tasking Analyst with {len(urls)} candidates.")
                        await self.analyst.analyze(urls, limit=max_leads)

        self.logger.info("Mission Completed Successfully.")
