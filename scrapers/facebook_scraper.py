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
            
            # Gestión de Sesión y LOGIN
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1"
            )
            page = await context.new_page()
            
            # 1. Navegación directa al Grupo (A veces Facebook permite ver si hay cookies previas)
            logger.info(f"🚀 Navegando a: {self.group_url}")
            await page.goto(self.group_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)

            # 2. DETECCIÓN Y GESTIÓN DE LOGIN / COOKIES
            # Si vemos campos de login o muros de cookies, actuamos
            if self.user and self.password:
                try:
                    # Limpieza de Cookies (Cualquier botón que parezca aceptar/rechazar)
                    cookie_btns = await page.locator('button:has-text("Aceptar"), button:has-text("Rechazar"), button:has-text("cookies")').all()
                    for b in cookie_btns:
                        if await b.is_visible(): await b.click()
                    
                    # ¿Estamos en una pantalla de login?
                    if await page.locator('input[name="email"]').is_visible():
                        logger.info(f"🔑 Muro de Login detectado. Identificando a {self.user}...")
                        await page.fill('input[name="email"]', self.user)
                        await page.fill('input[name="pass"]', self.password)
                        
                        # Click en el botón de login (con reintentos y selectores amplios)
                        login_selectors = ['button[name="login"]', 'button[type="submit"]', '[role="button"]:has-text("Entrar")', '[role="button"]:has-text("Log In")']
                        for sel in login_selectors:
                            try:
                                btn = page.locator(sel)
                                if await btn.is_visible():
                                    await btn.click(timeout=5000)
                                    break
                            except: continue
                        
                        await page.wait_for_timeout(5000)
                except Exception as e:
                    logger.warning(f"⚠️ Aviso en fase de acceso: {str(e)[:100]}")

            # 3. Excavación con ACUMULACIÓN GRANULAR
            logger.info("🚜 Aspirando contenido (Objetivo: 100 publicaciones brutas)...")
            unique_posts = set()
            
            for scroll_idx in range(25):
                # Expandimos los "Ver más"
                try:
                    view_more = await page.get_by_text("Ver más").all()
                    for b in view_more:
                        if await b.is_visible(): await b.click()
                except: pass
                
                # CAPTURA TODOTERRENO: Capturamos todo el texto y lo troceamos por marcadores de post
                full_text = await page.evaluate("document.body.innerText")
                
                # Facebook Móvil separa los posts con "Me gusta", "Compartir", "Comentar"
                # Usamos estos marcadores para trocear el chorro de texto
                markers = ["Compartir", "Comentar", "Me gusta", "Hace 1 día", "Hace 2 días"]
                pattern = "|".join(re.escape(m) for m in markers)
                raw_fragments = re.split(pattern, full_text)
                
                for frag in raw_fragments:
                    clean_frag = frag.strip()
                    if len(clean_frag) > 100: # Un anuncio real tiene cuerpo
                        unique_posts.add(clean_frag)
                
                await page.mouse.wheel(0, 1000)
                await page.wait_for_timeout(1000)
                
                if scroll_idx % 5 == 0:
                    logger.info(f"   🚜 Escaneo {scroll_idx}: {len(unique_posts)} fragmentos únicos detectados...")

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
