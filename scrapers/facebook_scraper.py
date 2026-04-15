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
                for scroll in range(30):
                    # 1. Comprobar que la página sigue viva
                    if page.is_closed(): break
                    
                    # 2. Expandir anuncios (Ver más)
                    try:
                        expand_btns = await page.get_by_text(re.compile(r"Ver más|See more", re.IGNORECASE)).all()
                        for b in expand_btns[:5]:
                            if await b.is_visible(): await b.click(timeout=500)
                    except: pass
                    
                    # 3. EXTRACCIÓN POR BLOQUES (Mucho más estable que re.split)
                    # Buscamos divs que contienen palabras clave de interacción
                    new_fragments = await page.evaluate("""() => {
                        const posts = [];
                        // Buscamos contenedores que parezcan anuncios
                        const elements = document.querySelectorAll('article, div[data-sigil="m-feed-voice-internal"], div._5r-k');
                        elements.forEach(el => posts.push(el.innerText));
                        
                        // Si no encuentra nada por selector, intentamos por densidad de texto
                        if (posts.length === 0) {
                            return document.body ? document.body.innerText.split(/Compartir|Share|Comment|Comentar/) : [];
                        }
                        return posts;
                    }""")
                    
                    for frag in new_fragments:
                        clean = frag.strip()
                        if len(clean) > 60: 
                            unique_posts.add(clean)
                    
                    if scroll % 5 == 0:
                        logger.info(f"🚜 Escaneo {scroll}: {len(unique_posts)} fragmentos únicos acumulados...")
                    
                    await page.mouse.wheel(0, 1500)
                    await page.wait_for_timeout(1500)

                # Mandamos los fragmentos a analizar con ESCUDO DE AHORRO
                valid_candidates = [p for p in unique_posts if any(k in p.lower() for k in [
                    'piso', 'casa', 'vivienda', 'alquiler', 'vendo', 'venta', 'chalet', 'inmueble', 
                    'hab', 'dorm', 'baño', 'estudio', 'loft', 'duplex', 'finca', 'apartamento', 
                    '€', 'euro', 'precio', 'm2', 'particular', 'inmobiliaria', 'comunidad'
                ])]
                
                logger.info(f"📑 Analizando {len(valid_candidates)} de {len(unique_posts)} candidatos con Escudo de Ahorro...")
                
                for post_text in valid_candidates:
                    if total_leads >= self.limit: break
                    
                    # Usamos "Facebook" como nombre de fuente limpio
                    ai_data = await self.analyst.parse_raw_text(post_text, "Facebook")
                    if ai_data:
                        # Generar hash para deduplicación
                        f_hash = hashlib.md5(f"{ai_data['title']}{ai_data['price']}".encode()).hexdigest()[:12]
                        if await self.is_already_scraped(f_hash): 
                            continue
                        
                        # Inyección en DB
                        ai_data["url"] = f"{group_url}?post_id={f_hash}"
                        success = await self.connector.upsert_property(ai_data)
                        
                        total_leads += 1
                        await self.mark_as_scraped(f_hash)
                        logger.info(f"✨ [{total_leads}/{self.limit}] Lead guardado: {ai_data['title']}")

            await browser.close()
            logger.info(f"🏁 Scraper finalizado. Total inyectado: {total_leads}")
            return total_leads

    async def scrape(self):
        # Mantenemos compatibilidad por si se llama individualmente
        return await self.scrape_multiple([self.group_url])
