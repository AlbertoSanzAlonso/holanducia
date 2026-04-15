import httpx
import logging
import json
import hashlib
import os
from agency.base_agent import BaseAgent
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class AnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__("Analyst")
        # Usamos variable de entorno para máxima seguridad (Evitamos bloqueos de GitHub)
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.openai_url = "https://api.openai.com/v1/chat/completions"

    async def parse_bulk_text(self, raw_text: str, source: str) -> List[Dict[str, Any]]:
        """Analiza un listado masivo y extrae múltiples propiedades de golpe (Modo Ahorro)"""
        logger.info(f"🧠 AI Bulk Extraction: Procesando listado masivo de {source}...")
        
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""
        Actúa como un experto buscador de inversiones inmobiliarias. 
        Analiza el siguiente texto extraído de un listado de {source} y extrae TODAS las propiedades que veas.
        
        Para cada propiedad, necesito este JSON:
        {{
            "title": "título descriptivo",
            "price": número (obligatorio),
            "city": "ciudad",
            "description": "resumen breve",
            "rooms": número,
            "url": "url del anuncio si aparece"
        }}
        
        Devuelve SOLO un array JSON de objetos. Si no hay propiedades claras, devuelve [].
        ¡IMPORTANTE! Si el precio no es un número claro, pon 0. No dejes el campo vacío.
        
        Texto a analizar:
        {raw_text[:12000]}
        """

        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.openai_url, json=payload, headers=headers)
                content = response.json()['choices'][0]['message']['content']
                
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                    
                data = json.loads(content)
                leads = data.get("properties", data) if isinstance(data, dict) else data
                
                for lead in leads:
                    lead["source"] = source
                    lead["price"] = self._clean_price(lead.get("price"))
                    
                logger.info(f"✅ Extracción masiva completada: {len(leads)} candidatos encontrados.")
                return leads
        except Exception as e:
            logger.error(f"❌ Error en extracción masiva AI: {e}")
            return []

    def _clean_price(self, price_val):
        try:
            return float(price_val)
        except:
            return 0

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
                
                # Saneamiento para evitar errores de base de datos (Not Null Constraint)
                if data.get("price") is None:
                    data["price"] = 0
                else:
                    try:
                        data["price"] = float(data["price"])
                    except:
                        data["price"] = 0
                
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
