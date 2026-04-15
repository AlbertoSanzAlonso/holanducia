import asyncio
import logging
import os
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class FacebookScraper(BaseScraper):
    def __init__(self, group_id: str, limit: int = 10):
        self.group_url = f"https://www.facebook.com/groups/{group_id}"
        super().__init__(source_name="Facebook", base_url=self.group_url)
        self.group_id = group_id
        self.limit = limit
        self.user = os.getenv("FB_USER")
        self.password = os.getenv("FB_PASSWORD")
        self.session_path = "/app/fb_session.json" # Para guardar el login

    async def scrape(self):
        logger.info(f"👥 Iniciando rascado de Facebook en el grupo: {self.group_url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            context_args = {}
            if os.path.exists(self.session_path):
                context_args["storage_state"] = self.session_path
            
            context = await browser.new_context(**context_args, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
            page = await context.new_page()

            # 1. ¿Necesitamos login?
            await page.goto("https://www.facebook.com")
            if "login" in page.url or await page.query_selector('input[name="email"]'):
                if not self.user or not self.password:
                    logger.error("❌ Se requiere login pero FB_USER/FB_PASSWORD no están configurados.")
                    await browser.close()
                    return
                
                logger.info("🔐 Realizando login en Facebook...")
                
                # Aceptar cookies
                cookie_selectors = ['button[data-cookiebanner="accept_button"]', 'button[title="Permitir todas las cookies"]', 'button:has-text("Aceptar todas")']
                for s in cookie_selectors:
                    try:
                        btn = await page.query_selector(s)
                        if btn: await btn.click(); await page.wait_for_timeout(2000); break
                    except: continue

                await page.fill('input[name="email"]', self.user)
                await page.fill('input[name="pass"]', self.password)
                
                # Intentar click en el botón de login explícitamente
                login_btn_selectors = ['button[name="login"]', 'button[type="submit"]', '[data-testid="royal_login_button"]']
                for s in login_btn_selectors:
                    try:
                        btn = await page.query_selector(s)
                        if btn: await btn.click(); break
                    except: continue
                else:
                    await page.keyboard.press("Enter")
                
                await page.wait_for_timeout(10000) 
                
                # Saltar el aviso de "Guardar información de inicio de sesión"
                save_info_btn = await page.query_selector('text="Ahora no"') or await page.query_selector('div[role="button"]:has-text("Ahora no")')
                if save_info_btn:
                    await save_info_btn.click()
                    await page.wait_for_timeout(2000)

                # Detectar Checkpoint de seguridad
                if "checkpoint" in page.url or await page.query_selector('input[name="approvals_code"]'):
                    logger.error(f"🚨 BLOQUEO DE SEGURIDAD detectado en {page.url}")
                    await self.connector.upsert_scraping_status("security_block", f"Facebook requiere verificación en {page.url}")
                    await context.storage_state(path=self.session_path)
                    await browser.close()
                    return

                await context.storage_state(path=self.session_path)
                logger.info(f"✅ Sesión guardada. Título actual: {await page.title()}")

            # 2. Ir al grupo
            await page.goto(self.group_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)
            
            # 3. Validar login de verdad
            is_logged_in = await page.query_selector('[aria-label="Notificaciones"]') or await page.query_selector('[aria-label="Perfil"]')
            if not is_logged_in:
                # Intento extra: a veces el selector de login sigue ahí pero estamos dentro
                if await page.query_selector('input[name="email"]'):
                    logger.error(f"❌ ERROR: Seguimos fuera o sesión invalidada. URL: {page.url}")
                    await browser.close()
                    return

            logger.info("✅ Login confirmado dentro del grupo.")

            # 4. Scroll para cargar contenido
            for _ in range(3):
                await page.mouse.wheel(0, 1500)
                await page.wait_for_timeout(3000)

            # 5. Extraer posts
            posts = await page.query_selector_all('div[role="feed"] > div, div[data-ad-preview="message"], div[data-testid="post_message"]')
            logger.info(f"📊 Analizando {len(posts)} posibles posts...")
            
            for i, post in enumerate(posts):
                if len(self.results) >= self.limit: break
                try:
                    content = await post.inner_text()
                    content_lower = content.lower()
                    
                    preview = content_lower[:50].replace('\n', ' ')
                    logger.info(f"  [Post {i+1}] Visto: {preview}...")
                    
                    is_real_estate = any(kw in content_lower for kw in ['piso', 'casa', 'alquiler', 'vendo', 'habitacion', 'estudio', 'chalet', 'inmueble'])
                    is_noise = any(kw in content_lower for kw in ['mueble', 'sofá', 'mesa', 'coche', 'busco', 'necesito'])
                    
                    if is_real_estate and not is_noise:
                        logger.info(f"  ✅ ¡Oportunidad detectada!")
                        self.results.append({
                            "title": content[:100] + "...",
                            "description": content,
                            "price": self._extract_price(content),
                            "city": "Málaga",
                            "source": "Facebook",
                            "url": self.group_url,
                            "images": ["https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=1000"]
                        })
                except: continue

            await browser.close()
            if self.results:
                await self.save_results()
                logger.info(f"🎉 Éxito: {len(self.results)} ofertas guardadas.")

    def _extract_price(self, text):
        import re
        match = re.search(r'(\d+[\d\.,]*)\s?€', text)
        if match:
            price_str = match.group(1).replace('.', '').replace(',', '.')
            try: return float(price_str)
            except: return 0
        return 0
