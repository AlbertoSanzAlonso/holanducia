import httpx
import logging
import json
import hashlib
import os
from agency.base_agent import BaseAgent
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class AnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__("Analyst")
        # Usamos variable de entorno para máxima seguridad (Evitamos bloqueos de GitHub)
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.openai_url = "https://api.openai.com/v1/chat/completions"

    async def parse_raw_text(self, raw_content: str, source: str = "Facebook") -> Optional[Dict[str, Any]]:
        """Extrae datos inmobiliarios estructurados usando OpenAI GPT-4o-mini"""
        self.logger.info("🧠 AI Analysis via OpenAI (Squadron Intel Active)...")
        
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system", 
                    "content": "Eres un analista experto en el mercado inmobiliario. Tu misión es extraer datos de posts de Facebook. SI EL POST NO ES UNA OFERTA DE VIVIENDA (ej. servicios de limpieza, quejas, publicidad), RESPONDE EXACTAMENTE 'NULL'. Si es una oferta, devuelve un JSON con: title, price (solo número), city, rooms, is_individual (boolean), description (resumen limpio)."
                },
                {"role": "user", "content": f"Post text: {raw_content}"}
            ],
            "response_format": {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.openai_url, json=payload, headers=headers)
                
                if response.status_code != 200:
                    self.logger.error(f"OpenAI Error: {response.text}")
                    return await self._fallback_parse(raw_content, source)
                
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                if "NULL" in content:
                    self.logger.warning("🚫 Post discarded: Non-real estate content detected by AI.")
                    return None
                
                data = json.loads(content)
                
                # Enriquecimiento y normalización
                content_hash = hashlib.md5(raw_content.encode()).hexdigest()[:10]
                data["external_id"] = f"{source[:2].upper()}-{content_hash}"
                data["url"] = f"https://facebook.com/groups/post_{content_hash}"
                data["source"] = source
                
                self.logger.info(f"✨ AI Verified Lead: {data.get('title')} ({data.get('price')}€)")
                return data

        except Exception as e:
            self.logger.error(f"AI Extraction failed: {e}")
            return await self._fallback_parse(raw_content, source)

    async def _fallback_parse(self, content: str, source: str) -> Optional[Dict[str, Any]]:
        """Emergency parsing if OpenAI is down"""
        content_lower = content.lower()
        if not any(kw in content_lower for kw in ['piso', 'casa', 'vivienda', 'alquiler', 'vendo']):
            return None
            
        content_hash = hashlib.md5(content.encode()).hexdigest()[:10]
        return {
            "external_id": f"{source[:2].upper()}-{content_hash}",
            "title": "Oportunidad detectada (AI Off)",
            "description": content[:300],
            "price": 0,
            "city": "Málaga",
            "source": source
        }
