import asyncio
import os
import re
import logging
import hashlib
import json
from playwright.async_api import async_playwright
from scrapers.base_scraper import BaseScraper
from scrapers.agency.analyst import AnalystAgent

logger = logging.getLogger(__name__)

class FacebookScraper(BaseScraper):
    def __init__(self, group_url, limit=50):
        super().__init__("Facebook", base_url="https://facebook.com")
        # Si nos pasan solo el ID, montamos la URL completa
        if group_url.isdigit() or not group_url.startswith("http"):
            self.group_url = f"https://m.facebook.com/groups/{group_url}"
        else:
            self.group_url = group_url.replace("www.facebook.com", "m.facebook.com")
            
        self.limit = limit
        self.results = []
        self.user = os.getenv("FB_USER")
        self.password = os.getenv("FB_PASSWORD")
        self.session_path = "/app/fb_session.json"
        self.analyst = AnalystAgent()

    async def scrape(self):
        logger.info(f"👥 [Infiltración Total] Grupo: {self.group_url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            # Gestión de Sesión
            context = await browser.new_context()
            page = await context.new_page()
            
            # Login simplificado (Asumimos cookies o login previo si existe)
            await page.goto(self.group_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            # 2. Excavación con ACUMULACIÓN GRANULAR
            logger.info(f"🚜 Aspirando contenido (Objetivo: {self.limit} publicaciones brutas)...")
            unique_posts = set()
            
            for scroll_idx in range(25):
                # Expandimos los "Ver más" para capturar el post entero
                try:
                    view_more = await page.get_by_text("Ver más").all()
                    for b in view_more:
                        if await b.is_visible(): await b.click()
                except: pass
                
                # Buscamos artículos individuales
                posts_locators = await page.locator('article, [role="article"]').all()
                for post in posts_locators:
                    try:
                        text = await post.inner_text()
                        # Limpieza básica de ruido
                        clean_text = re.sub(r'Compartir|Comentar|Me gusta|Seguir|Joined|Public group.*', '', text)
                        if len(clean_text) > 100: # Un anuncio de piso suele ser largo
                            unique_posts.add(clean_text.strip())
                    except: continue
                
                await page.mouse.wheel(0, 1000)
                await page.wait_for_timeout(1500)
                
                if scroll_idx % 5 == 0:
                    logger.info(f"   🚜 Escaneo {scroll_idx}: {len(unique_posts)} fragmentos únicos acumulados...")

            logger.info(f"📑 Analizando {len(unique_posts)} candidatos con OpenAI...")
            
            saved_count = 0
            for post_text in unique_posts:
                if saved_count >= self.limit: break
                
                # Comprobamos si el Director ya ha cumplido la cuota global
                if self.is_quota_met(): break
                
                # Pasamos el filtro de la IA
                ai_data = await self.analyst.parse_raw_text(post_text, self.source_name)
                
                if ai_data:
                    # Generamos ID único basado en el contenido para evitar duplicados semánticos
                    f_hash = hashlib.md5(f"{ai_data['title']}{ai_data['price']}{ai_data.get('city','')}".encode()).hexdigest()
                    unique_id = f"FB-{f_hash[:12]}"
                    
                    if await self.is_already_scraped(unique_id):
                        logger.info(f"⏭️  Omitiendo duplicado: {ai_data['title']}")
                        continue

                    # Guardamos
                    ai_data["url"] = f"{self.group_url}?post_id={f_hash[:16]}"
                    success = await self.connector.upsert_property(ai_data)
                    if success:
                        saved_count += 1
                        logger.info(f"✨ Nuevo Lead: {ai_data['title']} en {ai_data.get('city','Málaga')}")
                        await self.mark_as_scraped(unique_id)

            await browser.close()
            logger.info(f"✅ Extracción finalizada: {saved_count} candidatos reales inyectados.")
            return saved_count

    def is_quota_met(self) -> bool:
        # Nota: Esta función debería consultar al Director, pero por ahora simplificamos
        return False
