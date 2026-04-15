import asyncio
import logging
import os
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class FacebookScraper(BaseScraper):
    def __init__(self, group_id: str, limit: int = 10):
        # Usamos M.FACEBOOK para mayor estabilidad
        self.group_url = f"https://m.facebook.com/groups/{group_id}"
        super().__init__(source_name="Facebook", base_url=self.group_url)
        self.group_id = group_id
        self.limit = limit
        self.user = os.getenv("FB_USER")
        self.password = os.getenv("FB_PASSWORD")
        self.session_path = "/app/fb_session.json"

    async def scrape(self):
        logger.info(f"👥 [Modo Móvil] Iniciando infiltración en: {self.group_url}")
        
        async with async_playwright() as p:
            # Usamos un dispositivo móvil real para despistar
            iphone = p.devices['iPhone 13']
            browser = await p.chromium.launch(headless=True)
            
            context_args = {**iphone}
            if os.path.exists(self.session_path):
                context_args["storage_state"] = self.session_path
            
            context = await browser.new_context(**context_args)
            page = await context.new_page()

            # 1. Ir directo al grupo
            await page.goto(self.group_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)

            # 2. ¿Pide login?
            if await page.query_selector('input[name="email"]') or "login" in page.url:
                logger.info("🔐 Facebook Móvil pide credenciales. Iniciando login...")
                
                # Aceptar cookies en móvil
                try:
                    cookie_btn = await page.query_selector('button:has-text("Aceptar todas")') or await page.query_selector('button:has-text("Aceptar")')
                    if cookie_btn: await cookie_btn.click(); await page.wait_for_timeout(2000)
                except: pass

                if not self.user or not self.password:
                    logger.error("❌ FB_USER/FB_PASSWORD no configurados.")
                    await browser.close(); return

                await page.fill('input[name="email"]', self.user)
                await page.fill('input[name="pass"]', self.password)
                await page.click('button[name="login"]')
                
                # En móvil suele haber una pantalla intermedia de "Login con un toque"
                await page.wait_for_timeout(10000)
                
                # Detectar Checkpoint
                if "checkpoint" in page.url:
                    logger.error(f"🚨 BLOQUEO DE SEGURIDAD MÓVIL. URL: {page.url}")
                    await self.connector.upsert_scraping_status("security_block", "Facebook Móvil requiere verificación.")
                    await context.storage_state(path=self.session_path)
                    await browser.close(); return

                await context.storage_state(path=self.session_path)
                logger.info("✅ Sesión móvil guardada.")

            # 3. Validar si estamos dentro del grupo
            # En m.facebook los grupos tienen una estructura distinta
            await page.goto(self.group_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)
            
            is_in = "groups" in page.url and not (await page.query_selector('input[name="email"]'))
            if not is_in:
                logger.error(f"❌ Fallo crítico de infiltración móvil. URL: {page.url}")
                await browser.close(); return

            logger.info("✅ Infiltrado con éxito en el grupo móvil.")

            # 4. Scrolleo táctico
            for _ in range(5):
                await page.evaluate("window.scrollBy(0, 1200)")
                await page.wait_for_timeout(2500)

            # 5. Extraer posts (Selector móvil: suelen ser artículos o secciones con data-ft)
            posts = await page.query_selector_all('article, div[data-ft*="top_level_post_id"]')
            logger.info(f"📊 Analizando {len(posts)} posts móviles...")
            
            for i, post in enumerate(posts):
                if len(self.results) >= self.limit: break
                try:
                    content = await post.inner_text()
                    content_lower = content.lower()
                    
                    preview = content_lower[:50].replace('\n', ' ')
                    logger.info(f"  [Post {i+1}] Visto: {preview}...")
                    
                    is_real_estate = any(kw in content_lower for kw in ['piso', 'casa', 'alquiler', 'vendo', 'vivienda', 'chalet', 'inmueble'])
                    if is_real_estate:
                        logger.info(f"  ✅ ¡Oportunidad detectada en móvil!")
                        self.results.append({
                            "title": content[:100].replace('\n', ' ') + "...",
                            "description": content,
                            "price": self._extract_price(content_lower),
                            "city": "Málaga",
                            "source": "Facebook",
                            "url": self.group_url,
                            "images": ["https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=1000"]
                        })
                except: continue

            await browser.close()
            if self.results:
                await self.save_results()
                logger.info(f"🎉 Éxito móvil: {len(self.results)} ofertas capturadas.")

    def _extract_price(self, text):
        import re
        # Buscar patrones de precio (123.456€, 123000 €, etc)
        match = re.search(r'(\d+[\d\.,]*)\s?€', text)
        if match:
            p = match.group(1).replace('.', '').replace(',', '.')
            try: return float(p)
            except: return 0
        return 0
