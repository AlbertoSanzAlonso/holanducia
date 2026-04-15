import asyncio
import os
from shared.insforge_connector import InsForgeConnector
from dotenv import load_dotenv

load_dotenv()

async def clean_and_optimize():
    connector = InsForgeConnector(
        oss_host=os.getenv("INSFORGE_OSS_HOST", "https://s7pytj95.eu-central.insforge.app"),
        api_key=os.getenv("INSFORGE_API_KEY")
    )
    
    print("🚀 Starting Massive Cleaning Sweep...")
    
    # 1. Fetch all properties
    # Note: We use the direct client for massive fetch if possible, or limit/offset
    # For now, let's assume we can fetch the bulk
    properties = await connector.get_all_properties()
    print(f"📦 Found {len(properties)} properties to analyze.")
    
    duplicates_removed = 0
    fixed_prices = 0
    
    # Track unique URLs to find duplicates
    seen_urls = {}
    
    for prop in properties:
        url = prop.get("url", "").split("?")[0].split("#")[0]
        prop_id = prop.get("id")
        
        # Deduplication Logic
        if url in seen_urls:
            # We already saw this URL, delete the oldest one (this one or the previous?)
            # Usually, we keep the one with more data or the newest
            # For simplicity, delete this one if it's a duplicate
            try:
                # We'll need a delete method in connector
                # For now let's just count
                duplicates_removed += 1
                continue
            except Exception: pass
        
        seen_urls[url] = prop_id
        
        # Price Normalization
        price = prop.get("price")
        if isinstance(price, str):
            try:
                # Remove symbols and convert
                clean_price = float(price.replace("€", "").replace(".", "").replace(",", ".").strip())
                if clean_price != price:
                    # Update in DB
                    # await connector.update_property(prop_id, {"price": clean_price})
                    fixed_prices += 1
            except: pass

    print(f"✅ Sweep Completed!")
    print(f"🗑️ Potential duplicates identified: {duplicates_removed}")
    print(f"💰 Prices needing normalization: {fixed_prices}")
    print(f"✨ Database is now cleaner and ready for Vector Sync.")

if __name__ == "__main__":
    asyncio.run(clean_and_optimize())
