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
        self.group_url = self._format_url(group_url)
        self.limit = limit
        self.user = os.getenv("FB_USER")
        self.password = os.getenv("FB_PASSWORD")
        self.analyst = AnalystAgent()

    def _format_url(self, url):
        if url.isdigit() or not url.startswith("http"):
            return f"https://m.facebook.com/groups/{url}"
        return url.replace("www.facebook.com", "m.facebook.com")

    async def scrape_multiple(self, groups: list):
        """Recorre una lista de grupos compartiendo la misma sesión de login"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1"
            )
            page = await context.new_page()
            
            # --- FASE 1: LOGIN ÚNICO ---
            if self.user and self.password:
                logger.info(f"🔑 [Fase Login] Iniciando sesión única para {len(groups)} grupos...")
                try:
                    await page.goto("https://m.facebook.com/login", wait_until="networkidle")
                    # Limpiamos anuncios/cookies si aparecen
                    cookie_btns = await page.locator('button:has-text("Aceptar"), button:has-text("Rechazar"), button:has-text("cookies")').all()
                    for b in cookie_btns:
                        if await b.is_visible(): await b.click()
                    
                    await page.fill('input[name="email"]', self.user)
                    await page.fill('input[name="pass"]', self.password)
                    login_btn = page.locator('button[name="login"], button[type="submit"], [data-sigil="m_login_button"]')
                    await login_btn.first.click()
                    await page.wait_for_timeout(5000)
                    logger.info("✅ Login completado con éxito.")
                except Exception as e:
                    logger.warning(f"⚠️ Error en login: {e}. Intentando continuar como anónimo...")

            # --- FASE 2: RECORRIDO DE GRUPOS ---
            total_leads = 0
            for group_id in groups:
                if total_leads >= self.limit: break
                
                group_url = self._format_url(group_id)
                logger.info(f"👥 [Infiltración] Entrando en grupo: {group_url}")
                
                await page.goto(group_url, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)
                
                # Proceso de rascado del grupo
                unique_posts = set()
                for scroll in range(20): # 20 scrolls por grupo es suficiente para captar lo nuevo
                    # Expandir "Ver más"
                    try:
                        btns = await page.get_by_text("Ver más").all()
                        for b in btns[:3]: # Solo los primeros para no perder tiempo
                            if await b.is_visible(): await b.click()
                    except: pass
                    
                    full_text = await page.evaluate("document.body.innerText")
                    markers = ["Compartir", "Comentar", "Me gusta", "Hace 1 día", "Hace 2 días"]
                    pattern = "|".join(re.escape(m) for m in markers)
                    fragments = re.split(pattern, full_text)
                    
                    for frag in fragments:
                        if len(frag) > 120: unique_posts.add(frag.strip())
                    
                    await page.mouse.wheel(0, 1000)
                    await page.wait_for_timeout(1000)

                # Mandamos los fragmentos a analizar
                for post_text in unique_posts:
                    if total_leads >= self.limit: break
                    
                    ai_data = await self.analyst.parse_raw_text(post_text, group_id)
                    if ai_data:
                        # Deduplicación por contenido
                        f_hash = hashlib.md5(f"{ai_data['title']}{ai_data['price']}".encode()).hexdigest()[:12]
                        if await self.is_already_scraped(f_hash): continue
                        
                        ai_data["url"] = f"{group_url}?post_id={f_hash}"
                        success = await self.connector.upsert_property(ai_data)
                        if success:
                            total_leads += 1
                            await self.mark_as_scraped(f_hash)
                            logger.info(f"✨ [{total_leads}/{self.limit}] Lead Inyectado: {ai_data['title']}")

            await browser.close()
            return total_leads

    async def scrape(self):
        # Mantenemos compatibilidad por si se llama individualmente
        return await self.scrape_multiple([self.group_url])
