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
    scrapers = [
        MilanunciosScraper(city="madrid"),
        MilanunciosScraper(city="barcelona"),
        IdealistaScraper(city="madrid"),
        IdealistaScraper(city="barcelona")
    ]
    
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
