import asyncio
from milanuncios_scraper import MilanunciosScraper
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ScraperManager")

async def run_all_scrapers():
    scrapers = [
        MilanunciosScraper(city="madrid"),
        MilanunciosScraper(city="barcelona")
    ]
    
    logger.info(f"Starting execution of {len(scrapers)} scrapers...")
    
    tasks = [scraper.scrape() for scraper in scrapers]
    await asyncio.gather(*tasks)
    
    logger.info("All scrapers finished execution.")

if __name__ == "__main__":
    asyncio.run(run_all_scrapers())
