import asyncio
import logging
import os

from dotenv import load_dotenv

from scrapers.crawl4ai_sniper import Crawl4AISniper
from scrapers.db_connector import DatabaseConnector

DEFAULT_PORTALS = {
    "malaga": [
        "https://www.fotocasa.es/es/comprar/viviendas/malaga-provincia/todas-las-zonas/l",
        "https://www.habitaclia.com/comprar-vivienda-en-malaga/listado.htm",
        "https://www.pisos.com/venta/pisos-malaga/",
    ]
}


async def resolve_portal_urls() -> list[str]:
    connector = DatabaseConnector()
    settings = await connector.get_settings()
    portal_urls = (settings or {}).get("portal_urls") or []

    if isinstance(portal_urls, str):
        portal_urls = [u.strip() for u in portal_urls.split(",") if u.strip()]

    if portal_urls:
        return portal_urls

    city = ((settings or {}).get("city") or "malaga").split()[0].lower()
    return DEFAULT_PORTALS.get(city, DEFAULT_PORTALS["malaga"])


async def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    portal_urls = await resolve_portal_urls()
    limit = int(os.getenv("SNIPER_TEST_LIMIT", "3"))

    print(f"🎯 Portales a probar ({len(portal_urls)}):")
    for url in portal_urls:
        print(f"   - {url}")

    sniper = Crawl4AISniper(limit=limit)
    total = await sniper.scrape_portals(portal_urls)

    print(f"\n🏁 Resultado: {total} leads capturados (límite {limit})")


if __name__ == "__main__":
    asyncio.run(main())
