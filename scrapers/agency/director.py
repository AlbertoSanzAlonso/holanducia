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
        
        # CASO 1: Petición específica con URL
        if request and request.get('url'):
            await self._process_single_url(request['url'])
            return
        
        # CASO 2: Misión General Automática (Settings)
        settings = await self.connector.get_settings()
        if not settings: return

        cities = settings.get("cities") or [""]
        portals_raw = settings.get("portals")
        portals = [p.strip() for p in portals_raw.split(",")] if portals_raw else ["Facebook"]
        quota = settings.get("max_leads_per_portal", 10)
        
        for city in cities:
            for portal in portals:
                self.logger.info(f"Tasking Hunter with {portal} in {city}")
                
                urls = []
                if portal.lower() == "facebook":
                    fb_groups = settings.get("facebook_groups") or []
                    urls = [f"https://www.facebook.com/groups/{g}" for g in fb_groups]
                    if "facebook.com/groups/" in portal: urls.append(portal)
                else:
                    urls = await self.hunter.discover(portal, city)

                if urls and "facebook.com" in urls[0]:
                    await self._process_facebook_groups(urls, quota)
                else:
                    if urls:
                        await self.analyst.analyze(urls, limit=quota)

        self.logger.info("Mission Completed Successfully.")

    async def _process_facebook_groups(self, urls, quota):
        from scrapers.facebook_scraper import FacebookScraper
        total_saved = 0
        
        for fb_url in urls:
            if total_saved >= quota: break
            
            try:
                group_part = fb_url.split("groups/")[1].split("/")[0].split("?")[0]
                self.logger.info(f"🚀 Infiltrating FB Group: {group_part} (Need {quota - total_saved} more)")
                
                # REINTENTOS: Si no encontramos suficientes, bajamos más
                attempts = 0
                while total_saved < quota and attempts < 3:
                    attempts += 1
                    # Aumentamos agresividad en cada intento si no hay suficiente
                    limit_to_fetch = (quota - total_saved) * 15 
                    scraper = FacebookScraper(group_part, limit=max(limit_to_fetch, 50))
                    
                    leads = await scraper.scrape()
                    if not leads: break
                    
                    batch_saved = 0
                    for lead in leads:
                        if total_saved >= quota: break
                        
                        cleaned = await self.analyst.parse_raw_text(lead['description'], source="Facebook")
                        if cleaned:
                            cleaned['url'] = lead['url']
                            cleaned['images'] = lead['images']
                            await self.connector.upsert_property(cleaned)
                            total_saved += 1
                            batch_saved += 1
                    
                    self.logger.info(f"   📊 Attempt {attempts}: {batch_saved} real estate leads verified.")
                    if batch_saved == 0: break # Si en una tanda no hay nada inmobiliario, probablemente no haya más
                    
            except Exception as e:
                self.logger.error(f"Error in FB group scrape ({fb_url}): {e}")

    async def _process_single_url(self, url):
        if "facebook.com" in url:
            from scrapers.facebook_scraper import FacebookScraper
            try:
                group_part = url.split("groups/")[1].split("/")[0].split("?")[0]
                scraper = FacebookScraper(group_part, limit=30)
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
