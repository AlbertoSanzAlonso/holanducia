import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from scrapers.base_scraper import BaseScraper

DEFAULT_FIXTURE = Path(__file__).parent / "scrapers" / "fixtures" / "sample_listing.html"


class Crawl4AITestScraper(BaseScraper):
    async def scrape(self):
        pass


def default_test_url() -> str:
    return os.getenv("CRAWL4AI_TEST_URL", DEFAULT_FIXTURE.resolve().as_uri())


async def test_markdown():
    scraper = Crawl4AITestScraper("Crawl4AI-Test", "https://example.com")
    url = default_test_url()

    print(f"🕷️ Crawl4AI markdown test: {url}")
    data = await scraper.scrape_with_crawl4ai(url)

    if not data or not data.get("markdown"):
        print("❌ No se pudo extraer contenido.")
        return False

    preview = data["markdown"][:800].strip()
    print("\n✅ Markdown extraído correctamente")
    print(f"   Caracteres: {len(data['markdown'])}")
    print(f"\n--- Preview ---\n{preview}\n...")
    return True


async def test_schema():
    if not os.getenv("OPENAI_API_KEY"):
        print("⏭️ Saltando test con schema: falta OPENAI_API_KEY")
        return True

    scraper = Crawl4AITestScraper("Crawl4AI-Test", "https://example.com")
    url = default_test_url()
    schema = {
        "type": "object",
        "properties": {
            "listings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "price": {"type": "number"},
                        "city": {"type": "string"},
                    },
                },
            }
        },
    }

    print(f"\n🧠 Crawl4AI + LLM schema test: {url}")
    data = await scraper.scrape_with_crawl4ai(url, schema)

    if not data:
        print("❌ No se pudo extraer datos estructurados.")
        return False

    listings = data.get("listings", [])
    print(f"\n✅ Schema extraído: {len(listings)} anuncios detectados")
    for i, item in enumerate(listings[:3], start=1):
        print(f"   {i}. {item.get('title', 'N/A')} | {item.get('price', 0)} € | {item.get('city', 'N/A')}")
    return True


async def main():
    load_dotenv()
    markdown_ok = await test_markdown()
    schema_ok = await test_schema()

    if markdown_ok and schema_ok:
        print("\n🎉 Crawl4AI listo para probar en el flujo del proyecto.")
    else:
        print("\n⚠️ Algún test falló. Revisa logs y dependencias del navegador.")


if __name__ == "__main__":
    asyncio.run(main())
