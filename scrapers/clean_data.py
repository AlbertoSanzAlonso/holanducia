import asyncio
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:9000").rstrip("/")


async def clean_and_optimize():
    print("🚀 Starting Massive Cleaning Sweep...")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(f"{API_URL}/api/properties")
        response.raise_for_status()
        properties = response.json()

    print(f"📦 Found {len(properties)} properties to analyze.")

    duplicates_removed = 0
    fixed_prices = 0
    seen_urls = {}

    for prop in properties:
        url = prop.get("url", "").split("?")[0].split("#")[0]
        prop_id = prop.get("id")

        if url in seen_urls:
            duplicates_removed += 1
            continue

        seen_urls[url] = prop_id

        price = prop.get("price")
        if isinstance(price, str):
            try:
                clean_price = float(price.replace("€", "").replace(".", "").replace(",", ".").strip())
                if clean_price != price:
                    fixed_prices += 1
            except Exception:
                pass

    print("✅ Sweep Completed!")
    print(f"🗑️ Potential duplicates identified: {duplicates_removed}")
    print(f"💰 Prices needing normalization: {fixed_prices}")


if __name__ == "__main__":
    asyncio.run(clean_and_optimize())
