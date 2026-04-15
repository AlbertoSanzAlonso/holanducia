import httpx
from agency.base_agent import BaseAgent
from base_scraper import DEEP_PROPERTY_SCHEMA
from typing import Optional, Dict, Any

class AnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__("Analyst")

    async def analyze_lead(self, url: str) -> Optional[Dict[str, Any]]:
        self.logger.info(f"Deep analyzing lead: {url}")
        
        headers = {
            "Authorization": f"Bearer {self.firecrawl_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "url": url,
            "formats": ["json"],
            "jsonOptions": {
                "schema": DEEP_PROPERTY_SCHEMA
            },
            "waitFor": 3000, # Wait 3 seconds for dynamic content
            "mobile": True # Sometimes mobile sites are cleaner
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(f"{self.firecrawl_base}/scrape", json=payload, headers=headers)
                if response.status_code != 200:
                    self.logger.error(f"Scrape failed: {response.text}")
                    return None
                
                data = response.json()
                # Firecrawl v1 Json Format returns data in the 'json' key
                extracted = data.get("data", {}).get("json", {})
                
                # STRICT VALIDATION: Avoid empty or error values
                title = extracted.get("title", "").lower()
                price = extracted.get("price", 0)
                
                if not extracted or price == 0 or len(title) < 10 or "interrupción" in title or "error" in title:
                    self.logger.warning(f"Lead discarded due to poor quality or blockage: {extracted.get('title')} (Price: {price})")
                    return None
                
                # Ensure numerical types
                try:
                    extracted["price"] = float(price)
                    if "rooms" in extracted: extracted["rooms"] = int(extracted.get("rooms") or 0)
                    if "size_m2" in extracted: extracted["size_m2"] = float(extracted.get("size_m2") or 0)
                except Exception as e:
                    self.logger.warning(f"Data type conversion failed for {url}: {e}")
                
                # URL Normalization (remove query params)
                clean_url = url.split("?")[0].split("#")[0]
                
                # Dynamic ID Extraction
                parts = clean_url.rstrip("/").split("/")
                ext_id = parts[-1] if not parts[-1].isdigit() and len(parts) > 1 else parts[-1]
                if parts[-1].lower() in ['d', 'p', 'v']: # Common in Fotocasa/Pisos
                    ext_id = parts[-2]

                # Dynamic source from URL
                source_val = "Unknown"
                if "fotocasa" in clean_url: source_val = "Fotocasa"
                elif "habitaclia" in clean_url: source_val = "Habitaclia"
                elif "pisos.com" in clean_url: source_val = "Pisos.com"
                elif "idealista" in clean_url: source_val = "Idealista"

                # Normalize and add metadata
                property_data = {
                    "external_id": f"FC-{ext_id}",
                    "source": source_val,
                    "url": clean_url,
                    **extracted
                }
                
                self.logger.info(f"✅ Extracted Exact URL: {clean_url}")
                return property_data
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            return None
