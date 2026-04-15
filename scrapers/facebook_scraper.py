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
                page.mouse.wheel(0, 800)
                await asyncio.sleep(3)
                
                # 1. Primero EXPANDIMOS todo lo que haya (Ver más / See more)
                try:
                    expand_btns = await page.query_selector_all("text='Ver más', text='See more', text='... Ver más'")
                    for b in expand_btns: 
                        if await b.is_visible(): await b.click()
                except: pass
                
                # 2. Ahora CAPTURAMOS el texto completo desplegado
                visible_text = await page.evaluate("document.body.innerText")
                accumulated_text += "\n" + visible_text
                
                if scroll_idx % 5 == 0:
                    logger.info(f"   🚜 Escaneo {scroll_idx}: Profundizando en el feed...")
                await page.wait_for_timeout(2000)

            # 3. EXTRACCIÓN MASIVA SOBRE EL BLOQUE ACUMULADO
            # Usamos separadores más estables que no aparecen dentro del texto del anuncio
            split_pattern = r'Me gusta|Compartir|Me encanta|Comentar| \d+[mhj] | \d+d | Ayer | Just now'
            fragments = re.split(split_pattern, accumulated_text)
            logger.info(f"📑 Analizando {len(fragments)} fragmentos con radar ampliado...")
            
            seen_hashes = set()
            keywords = [
                'piso', 'casa', 'vivienda', 'alquiler', 'vendo', 'venta', 'chalet', 'inmueble', 
                'hab', 'dorm', 'baño', 'estudio', 'loft', 'duplex', 'finca', 'oportunidad',
                'apartamento', 'estudio', 'local', 'garaje', 'particular', 'dueño', 'directo',
                'REF.', 'REF:', 'referencia'
            ]
            for frag in fragments:
                if len(self.results) >= self.limit: break
                
                clean_frag = frag.strip()
                if len(clean_frag) < 50: continue
                
                f_hash = self._generate_stable_hash(clean_frag)
                
                if f_hash in seen_hashes: continue
                seen_hashes.add(f_hash)

                if any(kw in clean_frag.lower() for kw in keywords):
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

    def _generate_stable_hash(self, text: str) -> str:
        """Crea un hash que ignora ruidos temporales (tiempos, números, espacios)"""
        clean = text.lower()
        clean = re.sub(r'\d+', '', clean) 
        clean = re.sub(r'[^\w\s]', '', clean) 
        clean = "".join(clean.split()) 
        return hashlib.md5(clean.encode()).hexdigest()
