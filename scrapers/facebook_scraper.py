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
            context = await browser.new_context(**iphone)
            page = await context.new_page()

            await page.goto(self.group_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            if await page.query_selector('input[name="email"]') or "login" in page.url:
                await self._perform_login(page, context)

            # 2. Excavación con ACUMULACIÓN (Para que no se le olvide nada)
            logger.info(f"🚜 Aspirando contenido (Objetivo: {self.limit} publicaciones brutas para filtrar)...")
            accumulated_text = ""
            
            for scroll_idx in range(25):
                # Capturamos lo que hay visible ahora antes de que desaparezca
                visible_text = await page.evaluate('() => document.body.innerText')
                accumulated_text += "\n" + visible_text
                
                await page.evaluate("window.scrollBy(0, 3000)")
                await page.wait_for_timeout(2000)
                
                # Clic en "Ver más"
                try:
                    expand_btns = await page.query_selector_all('text="Ver más", text="See more", text="ver mais"')
                    for b in expand_btns: 
                        if await b.is_visible(): await b.click()
                except: pass
                
                if scroll_idx % 5 == 0:
                    logger.info(f"   🚜 Escaneo {scroll_idx}: Aspirador trabajando...")

            # 3. EXTRACCIÓN MASIVA SOBRE EL BLOQUE ACUMULADO
            # Usamos separadores más comunes en la versión móvil (Marcas de tiempo y botones de acción)
            split_pattern = r'Me gusta|Compartir|Me encanta|Comentar|Ver más|See more| \d+[mhj] | \d+d | Ayer | Just now'
            fragments = re.split(split_pattern, accumulated_text)
            logger.info(f"📑 Analizando {len(fragments)} fragmentos detectados por marcas de tiempo...")
            
            seen_hashes = set()
            for frag in fragments:
                if len(self.results) >= self.limit: break
                
                clean_frag = frag.strip()
                if len(clean_frag) < 80: continue
                
                f_hash = hashlib.md5(clean_frag.encode()).hexdigest()
                if f_hash in seen_hashes: continue
                seen_hashes.add(f_hash)

                if any(kw in clean_frag.lower() for kw in ['piso', 'casa', 'alquiler', 'vendo', 'hab', 'baño', 'estudio', 'loft']):
                    self.results.append({
                        "description": clean_frag,
                        "url": f"{self.group_url}?post_id={f_hash[:8]}",
                        "images": ["https://images.unsplash.com/photo-1560518883-ce09059eeffa"]
                    })

            await browser.close()
            logger.info(f"✅ Extracción finalizada: {len(self.results)} candidatos reales encontrados.")
            return self.results

    async def _perform_login(self, page, context):
        logger.info("🔐 Realizando login...")
        try:
            cookie_btn = await page.query_selector('button:has-text("Aceptar")')
            if cookie_btn: await cookie_btn.click()
        except: pass
        await page.fill('input[name="email"]', self.user)
        await page.fill('input[name="pass"]', self.password)
        await page.click('button[name="login"]')
        await page.wait_for_timeout(8000)
        await context.storage_state(path=self.session_path)
