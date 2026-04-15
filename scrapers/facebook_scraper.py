import asyncio
import logging
import os
import hashlib
import re
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class FacebookScraper(BaseScraper):
    def __init__(self, group_id: str, limit: int = 10):
        self.group_url = f"https://m.facebook.com/groups/{group_id}"
        super().__init__(source_name="Facebook", base_url=self.group_url)
        self.limit = limit
        self.user = os.getenv("FB_USER")
        self.password = os.getenv("FB_PASSWORD")
        self.session_path = "/app/fb_session.json"

    async def scrape(self):
        logger.info(f"👥 [Extracción Bruta] Grupo: {self.group_url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            iphone = p.devices['iPhone 13']
            context = await browser.new_context(**iphone)
            if os.path.exists(self.session_path):
                # Omitimos carga de cookies directa por ahora para asegurar login fresco si falla
                pass
            
            page = await context.new_page()

            # 1. Navegación y Login
            await page.goto(self.group_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            if await page.query_selector('input[name="email"]') or "login" in page.url:
                logger.info("🔐 Realizando login en versión móvil...")
                try:
                    cookie_btn = await page.query_selector('button:has-text("Aceptar")')
                    if cookie_btn: await cookie_btn.click(); await page.wait_for_timeout(2000)
                except: pass

                await page.fill('input[name="email"]', self.user)
                await page.fill('input[name="pass"]', self.password)
                await page.click('button[name="login"]')
                await page.wait_for_timeout(10000)
                
                # Saltar el "Guardar información de inicio de sesión"
                try:
                    not_now = await page.query_selector('text="Ahora no", text="Not Now"')
                    if not_now: await not_now.click(); await page.wait_for_timeout(3000)
                except: pass
                
                await context.storage_state(path=self.session_path)

            # 2. Bucle de Excavación Dinámica (Más agresivo)
            logger.info(f"🚜 Iniciando excavación dinámica (Objetivo: {self.limit} leads)...")
            scroll_cycles = 0
            
            for _ in range(20):
                await page.evaluate("window.scrollBy(0, 3000)")
                await page.wait_for_timeout(3000) # Más tiempo para cargar
                
                # Intentar pulsar "Ver más publicaciones" si aparece
                try:
                    more_btn = await page.query_selector('text="Ver más publicaciones", text="Show more posts"')
                    if more_btn: 
                        await more_btn.click()
                        logger.info("➕ Pulsado 'Ver más publicaciones'...")
                except: pass
                
                scroll_cycles += 1
                if scroll_cycles % 5 == 0:
                    # Selector más amplio para detectar posts móviles
                    current_items = await page.query_selector_all('div[role="article"], article, div[data-ft]')
                    logger.info(f"   🚜 Ciclo {scroll_cycles}: {len(current_items)} elementos detectados...")

            # 2.5 Expandir todo antes de extraer
            logger.info("📄 Expandiendo descripciones finales...")
            see_more_btns = await page.query_selector_all('text="Ver más", text="See more", text="Más", text="Ещё", text="ver mais"')
            for btn in see_more_btns:
                try: 
                    if await btn.is_visible(): 
                        await btn.click()
                except: continue
            await page.wait_for_timeout(2000)

            # 3. Captura con selector ultra-agresivo
            # Buscamos cualquier div que parezca un post por su estructura o contenido
            items = await page.query_selector_all('div[role="article"], article, div[data-ft]')
            logger.info(f"📊 {len(items)} posts en bruto encontrados. Procesando...")
            
            seen_texts = set()
            for item in items:
                if len(self.results) >= self.limit: break
                try:
                    text = await item.inner_text()
                    if len(text) < 60 or text in seen_texts: continue
                    seen_texts.add(text)
                    
                    # URL del post (buscando enlaces que funcionen)
                    post_url = self.group_url
                    links = await item.query_selector_all('a')
                    for l in links:
                        href = await l.get_attribute('href')
                        if href and ('story.php' in href or '/posts/' in href or '/permalink/' in href):
                            post_url = f"https://m.facebook.com{href}" if href.startswith('/') else href
                            break

                    # Imagen
                    img_el = await item.query_selector('img')
                    img_url = await img_el.get_attribute('src') if img_el else "https://images.unsplash.com/photo-1560518883-ce09059eeffa"
                    
                    self.results.append({
                        "description": text,
                        "url": post_url.split('?')[0],
                        "images": [img_url]
                    })
                except: continue

            await browser.close()
            return self.results
