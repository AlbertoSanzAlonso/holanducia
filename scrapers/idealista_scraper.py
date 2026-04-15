import asyncio
from playwright.async_api import async_playwright
try:
    from base_scraper import BaseScraper
except ImportError:
    from scrapers.base_scraper import BaseScraper
import logging
import random
import re
from typing import Optional

logger = logging.getLogger(__name__)

class IdealistaScraper(BaseScraper):
    def __init__(self, city: str = "madrid", settings: Optional[dict] = None):
        super().__init__(source_name="Idealista", base_url="idealista.com", settings=settings)
        self.city = city

    async def scrape(self):
        logger.info(f"Starting Independent Extraction for {self.city}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            # User agent de alta fidelidad
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            try:
                url = f"https://www.idealista.com/venta-viviendas/{self.city}-{self.city}/"
                logger.info(f"Infiltrating: {url}")
                
                # Navegación ultra-lenta para evitar detección
                await page.goto(url, wait_until="networkidle")
                await asyncio.sleep(random.uniform(5, 8))
                
                # Extraemos los datos básicos directamente de la lista (Evitamos entrar en detalles)
                items = await page.query_selector_all("article.item")
                logger.info(f"Scanning {len(items)} items on page...")

                for item in items:
                    try:
                        title_el = await item.query_selector(".item-link")
                        price_el = await item.query_selector(".item-price")
                        details_el = await item.query_selector(".item-detail-char")
                        img_el = await item.query_selector("img")
                        
                        if not title_el or not price_el: continue
                        
                        title = await title_el.inner_text()
                        url_prop = f"https://www.idealista.com{await title_el.get_attribute('href')}"
                        price_raw = await price_el.inner_text()
                        price = int(re.sub(r'[^\d]', '', price_raw))
                        
                        size_raw = await item.inner_text()
                        size_match = re.search(r'(\d+)\s*m²', size_raw)
                        size = int(size_match.group(1)) if size_match else 0
                        
                        img_url = await img_el.get_attribute("src") if img_el else ""

                        prop = {
                            "external_id": url_prop.split("/")[-2],
                            "source": self.source_name,
                            "url": url_prop,
                            "title": title,
                            "price": price,
                            "city": self.city.capitalize(),
                            "size_m2": size,
                            "images": [img_url] if img_url else [],
                            "description": "Auto-extraído de la lista general.",
                            "is_individual": "particular" in title.lower() or "individual" in title.lower(),
                        }
                        
                        if prop["price"] > 0 and prop["size_m2"] > 0:
                            self.results.append(prop)
                            logger.info(f"✅ Infiltrated Lead: {title} @ {price}€")
                            
                    except Exception as e:
                        logger.error(f"Failed to parse item: {e}")

            except Exception as e:
                logger.error(f"Infiltration failed: {e}")
            finally:
                await browser.close()

        await self.save_results()
        return self.results
