import httpx
import logging
import hashlib
import re
from agency.base_agent import BaseAgent
from base_scraper import DEEP_PROPERTY_SCHEMA
from typing import Optional, Dict, Any

class AnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__("Analyst")

    async def parse_raw_text(self, raw_content: str, source: str = "Facebook") -> Optional[Dict[str, Any]]:
        """Uses refined logic to extract structured data from raw social media text"""
        self.logger.info(f"AI Parsing raw {source} content...")
        
        try:
            content = raw_content.strip()
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            
            # 1. VALIDACIÓN: ¿Es realmente inmobiliario?
            keywords = ['piso', 'casa', 'vivienda', 'alquiler', 'vendo', 'chalet', 'inmueble', 'habitacion', 'estudio', 'apartment', 'home', 'loft', 'duplex', 'finca']
            is_real_estate = any(kw in content.lower() for kw in keywords)
            
            if not is_real_estate:
                self.logger.warning("🚫 Post descartado: No parece contenido inmobiliario.")
                return None

            # 2. Extraer precio con regex reforzada
            price = 0
            price_match = re.search(r'(\d+[\d\.,]*)\s?(€|euros|e)', content.lower())
            if price_match:
                p_str = price_match.group(1).replace('.', '').replace(',', '.')
                try: price = float(p_str)
                except: pass

            # 3. Título (Primera línea o resumen)
            title = lines[0][:80] if lines else "Oportunidad Facebook"
            
            content_hash = hashlib.md5(content.encode()).hexdigest()[:10]
            
            return {
                "external_id": f"{source[:2].upper()}-{content_hash}",
                "title": title,
                "description": content,
                "price": price,
                "city": "Málaga", 
                "source": source,
                "is_individual": any(kw in content.lower() for kw in ["particular", "dueño", "propietario"]),
                "rooms": self._extract_number(content, r'(\d+)\s?(hab|dorm)'),
                "size_m2": self._extract_number(content, r'(\d+)\s?(m2|metros|m²)'),
            }
        except Exception as e:
            self.logger.error(f"Raw parsing failed: {e}")
            return None

    def _extract_number(self, text: str, pattern: str) -> int:
        match = re.search(pattern, text.lower())
        if match:
            try: return int(match.group(1))
            except: return 0
        return 0

    async def analyze_lead(self, url: str) -> Optional[Dict[str, Any]]:
        self.logger.info(f"Deep analyzing lead: {url}")
        
        # Original Firecrawl logic remains as fallback for portals
        headers = {
            "Authorization": f"Bearer {self.firecrawl_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "url": url,
            "formats": ["json"],
            "jsonOptions": { "schema": DEEP_PROPERTY_SCHEMA },
            "waitFor": 3000,
            "mobile": True
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(f"{self.firecrawl_base}/scrape", json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    extracted = data.get("data", {}).get("json", {})
                    # Add essential metadata
                    extracted["url"] = url
                    extracted["external_id"] = f"EXT-{hashlib.md5(url.encode()).hexdigest()[:8]}"
                    return extracted
                return None
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            return None
