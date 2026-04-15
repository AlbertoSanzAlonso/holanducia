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
        logger.info(f"👥 [Infiltración Total] Grupo: {self.group_url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            iphone = p.devices['iPhone 13']
            context_args = {**iphone}
            if os.path.exists(self.session_path):
                context_args["storage_state"] = self.session_path
            
            context = await browser.new_context(**context_args)
            page = await context.new_page()

            # 1. Navegación y Login
            await page.goto(self.group_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)

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
                await context.storage_state(path=self.session_path)

            # 2. Scrolleo profundo para recabar datos
            logger.info("🚜 Descargando anuncios recientes...")
            for _ in range(6):
                await page.evaluate("window.scrollBy(0, 1500)")
                await page.wait_for_timeout(2500)

            # 2.5 Expandir todas las descripciones ("Ver más")
            logger.info("📄 Expandiendo descripciones largas...")
            see_more_btns = await page.query_selector_all('text="Ver más", text="See more", text="Más", text="Ещё"')
            for btn in see_more_btns:
                try:
                    if await btn.is_visible(): await btn.click()
                except: continue
            await page.wait_for_timeout(2000)

            # 3. Extracción con selectores móviles precisos
            posts = await page.query_selector_all('article, div[role="article"]')
            logger.info(f"📊 {len(posts)} publicaciones encontradas. Analizando calidad...")
            
            for i, post in enumerate(posts):
                if len(self.results) >= self.limit: break
                try:
                    text = await post.inner_text()
                    text_lower = text.lower()
                    
                    # Filtro de oportunidad
                    keywords = ['piso', 'casa', 'vivienda', 'alquiler', 'vendo', 'chalet', 'inmueble', 'habitacion', 'estudio']
                    noise = ['busco', 'necesito', 'demanda', 'mueble', 'sofá', 'coche']
                    
                    if any(k in text_lower for k in keywords) and not any(n in text_lower for n in noise):
                        # Extracción de imagen real
                        img_el = await post.query_selector('img')
                        img_url = await img_el.get_attribute('src') if img_el else "https://images.unsplash.com/photo-1560518883-ce09059eeffa"
                        
                        content_hash = hashlib.md5(text.encode()).hexdigest()[:12]
                        price = self._extract_price(text)
                        
                        # Buscar enlace real del post (suele estar en el timestamp)
                        post_url = self.group_url # Por defecto el grupo
                        link_el = await post.query_selector('a[href*="story.php"], a[href*="/posts/"], a[href*="/permalink/"]')
                        if link_el:
                            href = await link_el.get_attribute('href')
                            if href:
                                if href.startswith('/'): post_url = f"https://m.facebook.com{href}"
                                else: post_url = href

                        logger.info(f"  ✅ Detectado: {text[:40]}... (URL: {post_url[:30]}...)")
                        
                        self.results.append({
                            "external_id": f"FB-{content_hash}",
                            "title": text.split('\n')[0][:80] if '\n' in text else text[:80],
                            "description": text,
                            "price": price,
                            "city": "Málaga",
                            "source": "Facebook",
                            "url": post_url,
                            "images": [img_url],
                            "is_individual": "particular" in text_lower or "dueño" in text_lower
                        })
                except Exception as e:
                    logger.debug(f"Error en post {i}: {e}")
                    continue

            await browser.close()
            if self.results:
                await self.save_results()
                logger.info(f"🎉 Éxito: {len(self.results)} ofertas listas en HolanducIA.")

    def _extract_price(self, text):
        # Limpiar texto para buscar precios mejor
        text = text.replace('.', '').replace(',', '')
        match = re.search(r'(\d{3,6})\s?[€|euros|e]', text, re.IGNORE_DECOMPOSITION)
        if match:
            try: return float(match.group(1))
            except: return 0
        return 0
