from scrapers.agency.base_agent import BaseAgent
from typing import List
from playwright.async_api import async_playwright
import random
import asyncio

class HunterAgent(BaseAgent):
    def __init__(self):
        super().__init__("Hunter")

    async def discover_leads(self, city: str, portal: str, query: str) -> List[str]:
        self.logger.info(f"🔍 Discovery Phase: Infiltrating {portal} in {city} directly...")
        
        # Portal URL Mapping
        search_urls = {
            "Fotocasa": f"https://www.fotocasa.es/es/comprar/viviendas/{city}-provincia/todas-las-zonas/l",
            "Habitaclia": f"https://www.habitaclia.com/comprar-vivienda-en-{city}/listado.htm",
            "Pisos.com": f"https://www.pisos.com/venta/pisos-{city}/",
            "Facebook": f"https://www.facebook.com/groups/41757906864", # Grupo por defecto
            "Catastro": f"https://subastas.boe.es/subastas_ava.php?campo%5B0%5D=SUBASTA.ESTADO&dato%5B0%5D=PC&campo%5B1%5D=SUBASTA.TIPO_BIEN&dato%5B1%5D=I&campo%5B6%5D=BIEN.PROVINCIA&dato%5B6%5D={city.upper()}"
        }
        
        url = search_urls.get(portal)
        if not url: return []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(5)
                
                # Handle Cookie Consent (Didomi, etc)
                cookie_selectors = [
                    "#didomi-notice-agree-button",
                    "button[id*='accept']",
                    "button[class*='accept']",
                    ".sui-AtomButton--primary", # common in fotocasa
                    "#onetrust-accept-btn-handler"
                ]
                for selector in cookie_selectors:
                    try:
                        btn = await page.query_selector(selector)
                        if btn and await btn.is_visible():
                            await btn.click()
                            self.logger.info(f"Accepted cookies on {portal}")
                            await asyncio.sleep(2)
                            break
                    except: continue

                # Extract links from page
                links = await page.query_selector_all("a")
                valid_urls = []
                self.logger.info(f"Total links found on page: {len(links)}")
                
                for link in links:
                    href = await link.get_attribute("href")
                    if not href or len(href) < 10: continue
                    
                    # Normalize absolute URLs
                    full_url = href
                    if href.startswith("/"):
                        if "fotocasa" in url: full_url = "https://www.fotocasa.es" + href
                        elif "habitaclia" in url: full_url = "https://www.habitaclia.com" + href
                        elif "pisos" in url: full_url = "https://www.pisos.com" + href

                    clean_u = full_url.split("?")[0].split("#")[0].rstrip("/")
                    
                    # More generous filtering for listing pages
                    listing_patterns = ["/vivienda/", "/inmueble/", "/anuncio/", "/piso/", "/comprar/", "/venta/"]
                    is_listing = any(x in clean_u for x in listing_patterns)
                    is_main_portal = any(p.lower() in clean_u.lower() for p in ["fotocasa", "habitaclia", "pisos"])
                    
                    # Avoid list pages (usually end in / or /l or /listado)
                    is_not_list = not clean_u.endswith("/l") and not clean_u.endswith("/listado.htm") and not clean_u.endswith("/listado")
                    
                    if is_listing and is_main_portal and is_not_list:
                        valid_urls.append(clean_u)
                
                valid_urls = list(set(valid_urls))
                
                if not valid_urls:
                    self.logger.warning(f"No valid leads found. Sample links: {[l[:50] for l in [await a.get_attribute('href') for a in links[:5]] if l]}")
                
                self.logger.info(f"✨ Found {len(valid_urls)} leads on {portal} list page.")
                return valid_urls
                
            except Exception as e:
                self.logger.error(f"Direct infiltration failed for {portal}: {e}")
                return []
            finally:
                try:
                    await browser.close()
                except:
                    pass
