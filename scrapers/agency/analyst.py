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
        """AI-driven extraction from raw social media content"""
        self.logger.info(f"AI Analyzing raw {source} content...")
        
        try:
            content = raw_content.strip()
            
            # 1. VALIDACIÓN REFORZADA: ¿Es una oportunidad real?
            keywords = [
                'piso', 'casa', 'vivienda', 'alquiler', 'vendo', 'chalet', 'inmueble', 
                'hab', 'dorm', 'baño', 'estudio', 'loft', 'duplex', 'finca', 'oportunidad',
                'piso en', 'alquilo', 'particular', 'dueño', 'directo', 'reformado'
            ]
            content_lower = content.lower()
            is_real_estate = any(kw in content_lower for kw in keywords)
            
            # Descartar si huele a basura o búsqueda
            noise = ['busco', 'necesito', 'demanda', 'compro', 'mueble', 'sofá', 'coche', 'empleo', 'trabajo']
            if not is_real_estate or any(n in content_lower[:100] for n in noise):
                return None

            # 2. Extracción de Datos con Patrones Avanzados
            price = 0
            # Soporta: 850€, 1.200 €, 90.000 euros, 120k, 130.000e
            price_match = re.search(r'(\d+[\d\.,]*)\s?(€|euro|e\b|k\b)', content_lower)
            if price_match:
                p_str = price_match.group(1).replace('.', '').replace(',', '.')
                if 'k' in price_match.group(0): 
                    try: price = float(p_str) * 1000
                    except: pass
                else:
                    try: price = float(p_str)
                    except: pass

            # 3. Construcción de Título Inteligente
            # Buscamos la primera palabra clave para empezar el título desde ahí
            title = "Oportunidad Inmobiliaria"
            for kw in ['piso', 'casa', 'chalet', 'estudio', 'loft', 'duplex']:
                if kw in content_lower:
                    idx = content_lower.find(kw)
                    raw_title = content[idx:idx+70].split('\n')[0]
                    title = raw_title.capitalize()
                    break
            
            # 4. Detección de Ciudad
            city = "Málaga" # Default
            cities_to_check = ['marbella', 'benalmadena', 'torremolinos', 'fuengirola', 'mijas', 'estepona', 'nerja', 'rincon']
            for c in cities_to_check:
                if c in content_lower:
                    city = c.capitalize()
                    break

            content_hash = hashlib.md5(content.encode()).hexdigest()[:10]
            
            return {
                "external_id": f"{source[:2].upper()}-{content_hash}",
                "title": title,
                "description": content,
                "price": price,
                "city": city, 
                "source": source,
                "is_individual": any(kw in content_lower for kw in ["particular", "dueño", "propietario", "directo"]),
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
        # Mantenemos logic para portales...
        return None
