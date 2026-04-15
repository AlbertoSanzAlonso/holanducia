import asyncio
import logging
from scrapers.agency.director import DirectorAgent

async def run_controlled_test():
    logging.basicConfig(level=logging.INFO)
    director = DirectorAgent()
    
    print("🚀 Starting Controlled Test: Single Portal, 2 Leads...")
    
    # 1. HUNTER: Find potential leads for Pisos.com in Malaga
    # Using a very specific query to find something quickly
    potential_urls = await director.hunter.discover_leads("malaga", "Pisos.com", "con piscina")
    
    if not potential_urls:
        print("❌ No leads found during discovery.")
        return
        
    # Limit to top 20 for testing
    test_urls = potential_urls[:20]
    print(f"🎯 Testing Batch: {len(test_urls)} leads.")
    
    for url in test_urls:
        # Check if exists (to force fresh scrape if needed, I'll skip check for this test)
        print(f"📡 Analyzing: {url}")
        property_data = await director.analyst.analyze_lead(url)
        
        if property_data:
            print(f"✅ SUCCESS: Extracted {property_data['title']}")
            print(f"   💰 Price: {property_data['price']} €")
            print(f"   🚗 Parking: {property_data.get('has_parking')}")
            print(f"   🏊 Pool: {property_data.get('has_pool')}")
            
            # Save it
            await director.connector.upsert_property(property_data)
            print("   💾 Saved to Database.")
        else:
            print(f"⚠️ FAILED to extract data for {url}")

if __name__ == "__main__":
    asyncio.run(run_controlled_test())
