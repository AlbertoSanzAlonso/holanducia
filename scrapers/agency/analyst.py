import httpx
from agency.base_agent import BaseAgent
from base_scraper import DEEP_PROPERTY_SCHEMA
from typing import Optional, Dict, Any

class AnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__("Analyst")

    async def parse_raw_text(self, raw_content: str, source: str = "Facebook") -> Optional[Dict[str, Any]]:
        """Uses AI (Mocked or real LLM) to extract structured data from raw social media text"""
        self.logger.info(f"AI Parsing raw {source} content...")
        
        # En una fase real, aquí llamaríamos a OpenAI/Claude o a una Edge Function de InsForge.
        # Por ahora, implementamos una lógica de limpieza avanzada 'pseudo-AI'.
        
        try:
            # Limpieza básica
            content = raw_content.strip()
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            
            # Intentar extraer precio con lógica reforzada
            import re
            price = 0
            price_match = re.search(r'(\d+[\d\.,]*)\s?(€|euros|e)', content.lower())
            if price_match:
                p_str = price_match.group(1).replace('.', '').replace(',', '.')
                try: price = float(p_str)
                except: pass

            # Generar un título profesional (IA style)
            # Si la primera línea es muy corta, combinamos las dos primeras
            title = lines[0] if len(lines[0]) > 20 else " ".join(lines[:2])
            title = title[:80] + "..." if len(title) > 80 else title
            
            # Metadatos falsos o extraídos
            import hashlib
            content_hash = hashlib.md5(content.encode()).hexdigest()[:10]
            
            return {
                "external_id": f"{source[:2].upper()}-{content_hash}",
                "title": title,
                "description": content,
                "price": price,
                "city": "Málaga", # Opcional: extraer con IA
                "source": source,
                "is_individual": any(kw in content.lower() for kw in ["particular", "dueño", "propietario"]),
                "rooms": self._extract_number(content, r'(\d+)\s?(hab|dorm)'),
                "size_m2": self._extract_number(content, r'(\d+)\s?(m2|metros|m²)'),
            }
        except Exception as e:
            self.logger.error(f"Raw parsing failed: {e}")
            return None

    def _extract_number(self, text: str, pattern: str) -> int:
        import re
        match = re.search(pattern, text.lower())
        if match:
            try: return int(match.group(1))
            except: return 0
        return 0

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
