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
                await context.add_cookies((await asyncio.to_thread(self._load_session_cookies)))
            
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

            # 2. Scrolleo profundo
            for _ in range(5):
                await page.evaluate("window.scrollBy(0, 1500)")
                await page.wait_for_timeout(2500)

            # 2.5 Expandir "Ver más"
            see_more_btns = await page.query_selector_all('text="Ver más", text="See more", text="Más", text="Ещё"')
            for btn in see_more_btns:
                try: 
                    if await btn.is_visible(): await btn.click()
                except: continue

            # 3. Captura masiva para el Analista
            posts = await page.query_selector_all('article, div[role="article"]')
            logger.info(f"📊 {len(posts)} publicaciones capturadas. Enviando a la IA...")
            
            for post in posts:
                if len(self.results) >= self.limit: break
                try:
                    text = await post.inner_text()
                    if len(text) < 50: continue
                    
                    # URL Real
                    post_url = self.group_url
                    link_el = await post.query_selector('a[href*="story.php"], a[href*="/posts/"], a[href*="/permalink/"]')
                    if link_el:
                        href = await link_el.get_attribute('href')
                        if href:
                            post_url = f"https://m.facebook.com{href}" if href.startswith('/') else href

                    # Imagen
                    img_el = await post.query_selector('img')
                    img_url = await img_el.get_attribute('src') if img_el else "https://images.unsplash.com/photo-1560518883-ce09059eeffa"
                    
                    self.results.append({
                        "description": text, # Raw text para la IA
                        "url": post_url.split('?')[0],
                        "images": [img_url]
                    })
                except: continue

            await browser.close()
            return self.results

    def _load_session_cookies(self):
        import json
        try:
            with open(self.session_path, 'r') as f:
                return json.load(f).get('cookies', [])
        except: return []
