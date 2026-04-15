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

class MilanunciosScraper(BaseScraper):
    def __init__(self, city: str = "madrid", settings: Optional[dict] = None):
        super().__init__(source_name="Milanuncios", base_url="milanuncios.com", settings=settings)
        self.city = city

    async def scrape(self):
        logger.info(f"🚀 Iniciando SUPER-BARRIDO Milanuncios para {self.city}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                # Vamos a la lista de "Particulares" directamente si es posible
                url = f"https://www.milanuncios.com/venta-de-viviendas-en-{self.city}/?fromSearch=1&demanda=n"
                logger.info(f"Capturando lista: {url}")
                await page.goto(url, wait_until="networkidle", timeout=60000)
                
                # Scroll para cargar mínimo 100 anuncios
                for _ in range(5):
                    await page.mouse.wheel(0, 1500)
                    await asyncio.sleep(1)
                
                cards = await page.query_selector_all("article")
                logger.info(f"Procesando {len(cards)} anuncios encontrados...")

                for card in cards:
                    try:
                        text_content = await card.inner_text()
                        title_el = await card.query_selector("h2")
                        price_el = await card.query_selector(".ma-AdPrice-value")
                        link_el = await card.query_selector("a")
                        
                        if not title_el or not price_el: continue
                        
                        title = await title_el.inner_text()
                        price_raw = await price_el.inner_text()
                        price = int(re.sub(r'[^\d]', '', price_raw))
                        href = await link_el.get_attribute("href")
                        url_prop = f"https://www.milanuncios.com{href}" if href.startswith("/") else href
                        
                        # EXTRACCIÓN INTELIGENTE DE CARACTERÍSTICAS (Sin entrar al anuncio)
                        rooms_match = re.search(r'(\d+)\s*hab', text_content, re.IGNORECASE)
                        rooms = int(rooms_match.group(1)) if rooms_match else None
                        
                        has_terrace = any(x in text_content.lower() for x in ["terraza", "balcón", "exterior"])
                        has_garage = any(x in text_content.lower() for x in ["garaje", "parking", "cochera", "plaza"])
                        
                        size_match = re.search(r'(\d+)\s*m²', text_content)
                        size = int(size_match.group(1)) if size_match else 0

                        prop = {
                            "external_id": url_prop.split("/")[-1].replace(".htm", ""),
                            "source": self.source_name,
                            "url": url_prop,
                            "title": title,
                            "price": price,
                            "city": self.city.capitalize(),
                            "neighborhood": self.city.capitalize(), # Por ahora usamos la ciudad como zona si no hay más info
                            "size_m2": size,
                            "rooms": rooms,
                            "description": text_content[:500], # Guardamos el snippet para búsqueda directa
                            "images": [],
                            "opportunity_score": 80 if has_terrace or has_garage else 60,
                            "opportunity_reasons": []
                        }
                        
                        if has_terrace: prop["opportunity_reasons"].append("☀️ Terraza/Exterior")
                        if has_garage: prop["opportunity_reasons"].append("🚗 Garaje/Parking")
                        
                        if prop["price"] > 10000:
                            self.results.append(prop)
                    except: continue

            except Exception as e:
                logger.error(f"Error en super-barrido: {e}")
            finally:
                await browser.close()

        # GUARDADO MASIVO (Forzamos el guardado de todo lo capturado)
        await self.save_results()
        logger.info(f"✨ Ciclo completado: {len(self.results)} leads listos para mostrar.")
        return self.results
