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
            url = request['url']
            if "facebook.com" in url:
                from scrapers.facebook_scraper import FacebookScraper
                try:
                    group_part = url.split("groups/")[1].split("/")[0].split("?")[0]
                    scraper = FacebookScraper(group_part)
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
                return
        
        # CASO 2: Misión General Automática (Settings)
        settings = await self.connector.get_settings()
        if not settings: return

        cities = settings.get("cities") or [""]
        portals_raw = settings.get("portals")
        portals = [p.strip() for p in portals_raw.split(",")] if portals_raw else ["Facebook"]
        max_leads = settings.get("max_leads_per_portal", 10)
        
        for city in cities:
            for portal in portals:
                self.logger.info(f"Tasking Hunter with {portal} in {city}")
                
                if "facebook.com/groups/" in portal:
                    urls = [portal]
                else:
                    urls = await self.hunter.discover(portal, city)

                if urls and "facebook.com" in urls[0]:
                    from scrapers.facebook_scraper import FacebookScraper
                    for fb_url in urls:
                        try:
                            group_part = fb_url.split("groups/")[1].split("/")[0].split("?")[0]
                            self.logger.info(f"🚀 Infiltrating FB Group: {group_part}")
                            scraper = FacebookScraper(group_part, limit=50) # Pool grande para elegir
                            leads = await scraper.scrape()
                            if leads:
                                count = 0
                                for lead in leads:
                                    if count >= max_leads: break
                                    cleaned = await self.analyst.parse_raw_text(lead['description'], source="Facebook")
                                    if cleaned:
                                        cleaned['url'] = lead['url']
                                        cleaned['images'] = lead['images']
                                        await self.connector.upsert_property(cleaned)
                                        count += 1
                                self.logger.info(f"✅ Mission Success: {count} verified leads saved.")
                        except Exception as e:
                            self.logger.error(f"Error in FB group scrape ({fb_url}): {e}")
                else:
                    # OTROS PORTALES
                    if urls:
                        self.logger.info(f"Tasking Analyst with {len(urls)} candidates.")
                        await self.analyst.analyze(urls, limit=max_leads)

        self.logger.info("Mission Completed Successfully.")
