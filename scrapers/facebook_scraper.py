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
            # Gestión de Sesión y LOGIN (Forzando Inglés para estabilidad)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
                locale="en-US"
            )
            page = await context.new_page()
            
            # 1. FASE LOGIN
            if self.user and self.password:
                logger.info(f"🔑 [Fase Login] Identificando a {self.user}...")
                try:
                    await page.goto("https://m.facebook.com/login", wait_until="networkidle")
                    
                    # Llenamos campos (Asegurando que sean los correctos)
                    await page.wait_for_selector('input[name="email"]', timeout=10000)
                    await page.fill('input[name="email"]', self.user)
                    await page.fill('input[name="pass"]', self.password)
                    
                    # Buscamos el botón de login real con MIRADA QUIRÚRGICA
                    # Prioridad 1: Atributo técnico de Facebook. Prioridad 2: Texto claro.
                    login_selectors = [
                        '[data-sigil="m_login_button"]',
                        'button[name="login"]',
                        'button:has-text("Log In")',
                        'button:has-text("Entrar")'
                    ]
                    
                    for sel in login_selectors:
                        try:
                            # Ignoramos botones de "Cancelar" o "Atrás" que suelen ser clases como 'dialog-cancel-button'
                            btn = page.locator(sel).filter(has_not_text="Cancel").filter(has_not_text="Back").filter(has_not_text="Atrás")
                            if await btn.is_visible():
                                await btn.click(timeout=5000)
                                break
                        except: continue
                    
                    await page.wait_for_timeout(5000)
                    logger.info("✅ Login procesado.")
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
                for scroll in range(30): # Aumentamos profundidad a 30 scrolls
                    # Expandir "Ver más" (imprescindible para ver el anuncio completo)
                    try:
                        btns = await page.get_by_text("Ver más").all()
                        for b in btns[:5]:
                            if await b.is_visible(): await b.click()
                    except: pass
                    
                    full_text = await page.evaluate("document.body.innerText")
                    # Marcadores bilingües
                    markers = [
                        "Compartir", "Share", 
                        "Comentar", "Comment", 
                        "Me gusta", "Like", 
                        "Just now", "Ahora mismo"
                    ]
                    pattern = "|".join(re.escape(m) for m in markers)
                    fragments = re.split(pattern, full_text)
                    
                    for frag in fragments:
                        # Bajamos el listón a 50 caracteres para no perder anuncios cortos
                        if len(frag.strip()) > 50: 
                            unique_posts.add(frag.strip())
                    
                    await page.mouse.wheel(0, 1200)
                    await page.wait_for_timeout(1200)

                # Mandamos los fragmentos a analizar
                for post_text in unique_posts:
                    if total_leads >= self.limit: break
                    
                    # Usamos "Facebook" como nombre de fuente limpio
                    ai_data = await self.analyst.parse_raw_text(post_text, "Facebook")
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
