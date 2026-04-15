import asyncio
from scrapers.agency.hunter import HunterAgent
from scrapers.agency.analyst import AnalystAgent
from scrapers.agency.base_agent import BaseAgent

class DirectorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Director")
        self.hunter = HunterAgent()
        self.analyst = AnalystAgent()

    async def execute_mission(self):
        self.logger.info("Starting Mission: Massive Market Infiltration")
        
        settings = await self.connector.get_settings()
        if not settings:
            self.logger.error("Could not fetch settings. Mission aborted.")
            return

        cities_raw = settings.get("cities", "madrid")
        if isinstance(cities_raw, list):
            cities = cities_raw
        else:
            cities = cities_raw.split(",")
            
        max_price = settings.get("max_price", 500000)
        max_leads = settings.get("max_leads_per_portal", 10)
        
        # Dynamic Portals from settings (comma separated string)
        portals_raw = settings.get("portals")
        if portals_raw:
            portals = [p.strip() for p in portals_raw.split(",")]
        else:
            portals = ["Fotocasa", "Habitaclia", "Pisos.com"]
        
        for city in cities:
            city = str(city).strip()
            for portal in portals:
                # 1. HUNTER: Find potential leads
                potential_urls = await self.hunter.discover_leads(city, portal, f"hasta {max_price}€")
                
                # 2. DIRECTOR: Filter and LIMIT (SAVE CREDITS!)
                new_urls = []
                for url in potential_urls:
                    if len(new_urls) >= max_leads: break
                    if not await self.connector.check_property_exists(url):
                        new_urls.append(url)
                    else:
                        self.logger.info(f"Skipping existing lead: {url}")

                self.logger.info(f"Tasking Analyst with {len(new_urls)} new leads (Limit: {max_leads}).")

                # 3. ANALYST: Deep scrape new leads
                for url in new_urls:
                    property_data = await self.analyst.analyze_lead(url)
                    if property_data:
                        # 4. SAVE: Persist to InsForge
                        try:
                            await self.connector.upsert_property(property_data)
                            self.logger.info(f"Mission Success: Saved {property_data['title']}")
                        except Exception as e:
                            self.logger.error(f"Persistence error: {e}")
                    
                    # Small delay to respect rate limits
                    await asyncio.sleep(1)

        self.logger.info("Mission Completed.")

if __name__ == "__main__":
    director = DirectorAgent()
    asyncio.run(director.execute_mission())
