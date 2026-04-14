import asyncio
from playwright.async_api import async_playwright
try:
    from base_scraper import BaseScraper
except ImportError:
    from scrapers.base_scraper import BaseScraper
import logging
import re
import random

import logging
import re
import random
from typing import Optional, List

logger = logging.getLogger(__name__)

class IdealistaScraper(BaseScraper):
    def __init__(self, city: str = "madrid", settings: Optional[dict] = None):
        max_price = settings.get("max_price") if settings else None
        
        # Idealista URLs for filtering: https://www.idealista.com/venta-viviendas/madrid-madrid/precio-max-300000/
        base_url = f"https://www.idealista.com/venta-viviendas/{city}-{city}/"
        if max_price:
            base_url += f"precio-max-{int(max_price)}/"
            
        super().__init__(source_name="Idealista", base_url=base_url, settings=settings)

    async def scrape(self):
        logger.info(f"Starting {self.source_name} scrape for {self.base_url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            # Use a very specific context to avoid detection
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            try:
                # Add some random delay
                await asyncio.sleep(random.uniform(1, 3))
                
                logger.info(f"Navigating to {self.base_url}")
                await page.goto(self.base_url, wait_until="domcontentloaded")
                
                # Check for "Robot detected" or similar
                if "un reto" in (await page.title()).lower() or "captcha" in (await page.content()).lower():
                    logger.error("Idealista CAPTCHA detected. Blocking further requests.")
                    await browser.close()
                    return []

                # Handle cookies
                try:
                    cookie_button = await page.get_by_role("button", name="Aceptar").first
                    if await cookie_button.is_visible():
                        await cookie_button.click()
                except:
                    pass

                # Wait for listings
                await page.wait_for_selector(".item", timeout=10000)
                
                cards = await page.query_selector_all(".item")
                logger.info(f"Found {len(cards)} property cards")

                for card in cards:
                    try:
                        # 1. Extract Data
                        title_el = await card.query_selector(".item-link")
                        title = await title_el.inner_text() if title_el else "No Title"
                        href = await title_el.get_attribute("href") if title_el else ""
                        url = f"https://www.idealista.com{href}"
                        
                        price_el = await card.query_selector(".item-price")
                        price_text = await price_el.inner_text() if price_el else "0"
                        price = float(re.sub(r'[^\d.]', '', price_text.replace('.', '').replace(',', '.')))
                        
                        external_id = href.split("/")[-2] if "/" in href else "unknown"

                        # Identify 'Particular'
                        # Idealista often has a 'Particular' tag or 'Contactar' button differences
                        card_text = await card.inner_text()
                        is_individual = "Particular" in card_text
                        
                        prop = {
                            "external_id": external_id,
                            "source": self.source_name,
                            "url": url,
                            "title": title,
                            "price": price,
                            "is_individual": is_individual,
                            "is_agency": not is_individual,
                            "city": "Madrid",
                        }
                        
                        self.results.append(prop)
                        
                    except Exception as e:
                        logger.warning(f"Error parsing Idealista card: {e}")

            except Exception as e:
                logger.error(f"Failed to scrape Idealista: {e}")
            finally:
                await browser.close()
            
        logger.info(f"Extracted {len(self.results)} properties from Idealista. Saving...")
        await self.save_results()
        return self.results

if __name__ == "__main__":
    scraper = IdealistaScraper()
    asyncio.run(scraper.scrape())
