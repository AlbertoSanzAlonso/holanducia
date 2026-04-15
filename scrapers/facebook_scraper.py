import asyncio
import logging
import os
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from scrapers.base_scraper import BaseScraper

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
            # Iniciamos el navegador en modo "sigilo" (simplificado)
            browser = await p.chromium.launch(headless=True)
            
            # Intentamos cargar la sesión previa para no loguearnos siempre
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
                await page.fill('input[name="email"]', self.user)
                await page.fill('input[name="pass"]', self.password)
                await page.click('button[name="login"]')
                await page.wait_for_timeout(5000) # Esperamos que entre
                
                # Guardamos la sesión para la próxima vez
                await context.storage_state(path=self.session_path)
                logger.info("✅ Sesión guardada.")

            # 2. Ir al grupo
            await page.goto(self.group_url)
            await page.wait_for_timeout(3000)

            # 3. Extraer posts (Scrolleo un poco)
            for _ in range(3): # Scroll 3 veces para captar posts
                await page.mouse.wheel(0, 1000)
                await page.wait_for_timeout(2000)

            # Palabras clave que definen una oportunidad inmobiliaria
            KEYWORDS = ["piso", "casa", "vivienda", "inmueble", "terreno", "parcela", "alquilo", "vendo", "finca", "chalet", "estudio", "loft", "duplex"]
            # Palabras que suelen indicar ruido (no inmobiliario)
            NOISE = ["coche", "moto", "mueble", "sofá", "tv", "empleo", "trabajo", "regalo", "iphone"]

            # Buscamos los contenedores de los posts
            posts = await page.query_selector_all('div[role="feed"] > div, div[role="main"] div[data-ad-preview="message"]')

            logger.info(f"📊 Analizando {len(posts)} posibles posts...")
            
            for post in posts:
                if len(self.results) >= self.limit:
                    break
                try:
                    content = await post.inner_text()
                    content_lower = content.lower()
                    
                    # 1. Filtro rápido de palabras clave
                    has_keyword = any(kw in content_lower for kw in KEYWORDS)
                    is_noise = any(ns in content_lower for ns in NOISE)
                    
                    if has_keyword and not is_noise:
                        # 2. Si pasa el filtro, lo procesamos
                        logger.info(f"✨ ¡Oportunidad detectada!: {content[:60]}...")
                        
                        self.results.append({
                            "source": "Facebook",
                            "url": f"{self.group_url}",
                            "title": content[:50].replace("\n", " ") + "...",
                            "description": content,
                            "city": "Por determinar", # Habría que extraer con regex o IA
                            "price": 0, # Extraer con regex
                            "is_active": True
                        })
                    else:
                        logger.debug(f"🗑️ Post ignorado (Ruido o no inmobiliario): {content[:40]}...")
                except Exception as e:
                    logger.error(f"⚠️ Error al procesar un post de FB: {e}")
                    continue

            await browser.close()
            
            if self.results:
                await self.save_results()
                logger.info(f"🎉 Se han guardado {len(self.results)} oportunidades de Facebook.")

if __name__ == "__main__":
    # Prueba rápida
    scraper = FacebookScraper("41757906864")
    asyncio.run(scraper.scrape())
