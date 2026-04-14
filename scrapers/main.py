import asyncio
from milanuncios_scraper import MilanunciosScraper
from idealista_scraper import IdealistaScraper
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ScraperManager")

from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def run_all_scrapers():
    from shared.insforge_connector import InsForgeConnector
    connector = InsForgeConnector(
        oss_host="https://s7pytj95.eu-central.insforge.app",
        api_key="ik_0ed6e333e7a2e51c6c94939d8d8afbcf"
    )
    
    settings = await connector.get_settings()
    if not settings:
        logger.warning("No settings found, using defaults.")
        cities = ["madrid", "barcelona"]
    else:
        cities = settings.get("cities", ["madrid", "barcelona"])
        logger.info(f"Using settings: {settings}")

    scrapers = []
    for city in cities:
        scrapers.append(MilanunciosScraper(city=city))
        scrapers.append(IdealistaScraper(city=city))
    
    logger.info(f"Starting execution of {len(scrapers)} scrapers...")
    tasks = [scraper.scrape() for scraper in scrapers]
    await asyncio.gather(*tasks)
    logger.info("All scrapers finished execution.")

async def main():
    scheduler = AsyncIOScheduler()
    # Run once at startup
    await run_all_scrapers()
    # Then schedule every 30 minutes
    scheduler.add_job(run_all_scrapers, 'interval', minutes=30)
    scheduler.start()
    
    logger.info("Scheduler started. Running every 30 minutes.")
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    asyncio.run(main())
