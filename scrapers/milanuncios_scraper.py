import asyncio
from playwright.async_api import async_playwright
try:
    from base_scraper import BaseScraper
except ImportError:
    from scrapers.base_scraper import BaseScraper
import logging
import re
from typing import Optional, List

logger = logging.getLogger(__name__)

class MilanunciosScraper(BaseScraper):
    def __init__(self, city: str = "madrid", settings: Optional[dict] = None):
        max_price = settings.get("max_price") if settings else None
        rooms = settings.get("min_rooms") if settings else None
        
        base_url = f"https://www.milanuncios.com/inmobiliaria-en-{city}/"
        query_params = ["fromSearch=1"]
        if max_price: query_params.append(f"hasta={max_price}")
        if rooms: query_params.append(f"habitaciones={rooms}")
        
        base_url += "?" + "&".join(query_params)
        super().__init__(source_name="Milanuncios", base_url=base_url, settings=settings)

    async def scrape(self):
        logger.info(f"Starting {self.source_name} scrape for {self.base_url}")
        
        async with async_playwright() as p:
            # Launch browser with human-like parameters
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Navigate to the listings
            await page.goto(self.base_url, wait_until="domcontentloaded")
            
            # Handle cookies if present (common in Europe)
            try:
                cookie_button = await page.get_by_role("button", name=re.compile("Aceptar", re.I)).first
                if await cookie_button.is_visible():
                    await cookie_button.click()
            except:
                pass

            # Wait for list to load
            await page.wait_for_selector("article", timeout=10000)
            
            # Extract items
            cards = await page.query_selector_all("article")
            logger.info(f"Found {len(cards)} property cards")

            for card in cards:
                try:
                    # 1. Extract Basic Data
                    title_el = await card.query_selector("h3, .ma-AdCardV2-title")
                    title = await title_el.inner_text() if title_el else "No Title"
                    
                    price_el = await card.query_selector(".ma-AdValue-value")
                    price_text = await price_el.inner_text() if price_el else "0"
                    price = float(re.sub(r'[^\d.]', '', price_text.replace('.', '').replace(',', '.')))
                    
                    url_el = await card.query_selector("a")
                    href = await url_el.get_attribute("href") if url_el else ""
                    url = f"https://www.milanuncios.com{href}" if href.startswith("/") else href
                    
                    external_id = url.split("-")[-1].replace(".htm", "") if "-" in url else "unknown"

                    # 2. Identify 'Particular'
                    # Look for tags or labels
                    card_text = await card.inner_text()
                    is_individual = "Particular" in card_text
                    
                    # 3. Create Property Object
                    prop = {
                        "external_id": external_id,
                        "source": self.source_name,
                        "url": url,
                        "title": title,
                        "price": price,
                        "is_individual": is_individual,
                        "is_agency": not is_individual,
                        "city": "Madrid", # Default for now
                    }
                    
                    self.results.append(prop)
                    
                except Exception as e:
                    logger.warning(f"Error parsing card: {e}")

            await browser.close()
            
        logger.info(f"Extracted {len(self.results)} properties. Saving...")
        await self.save_results()
        return self.results

if __name__ == "__main__":
    scraper = MilanunciosScraper()
    asyncio.run(scraper.scrape())
