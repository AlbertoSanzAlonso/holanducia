import httpx
import logging
import hashlib
import re
import os
from agency.base_agent import BaseAgent
from typing import Optional, Dict, Any

class AnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__("Analyst")
        self.api_url = os.getenv("INSFORGE_URL")
        self.api_key = os.getenv("INSFORGE_ANON_KEY")
        # El endpoint de las funciones suele ser diferente al de la DB
        self.functions_url = self.api_url.replace(".eu-central", ".functions") if self.api_url else ""

    async def parse_raw_text(self, raw_content: str, source: str = "Facebook") -> Optional[Dict[str, Any]]:
        """Uses LLM-powered Edge Function to parse noisy content"""
        self.logger.info(f"🧠 AI Parsing noisy {source} content via LLM...")
        
        try:
            # Mandamos el contenido bruto a la función de análisis de IA de InsForge
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.functions_url}/analyze-property",
                    json={
                        "raw_text": raw_content,
                        "url": f"https://facebook.com/groups/radar?id={hashlib.md5(raw_content.encode()).hexdigest()[:8]}"
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    ai_data = response.json()
                    
                    # Si la IA dice que es una oportunidad baja o no es inmobiliario, descartamos
                    if ai_data.get('opportunity_score', 0) < 30 or not ai_data.get('title'):
                        self.logger.warning("🚫 Post descartado: No parece contenido inmobiliario de interés.")
                        return None
                    
                    # Enriquecemos con los campos necesarios para la DB
                    content_hash = hashlib.md5(raw_content.encode()).hexdigest()[:10]
                    ai_data["external_id"] = f"{source[:2].upper()}-{content_hash}"
                    ai_data["source"] = source
                    ai_data["description"] = raw_content # Guardamos el original por si acaso
                    
                    self.logger.info(f"✅ AI Verified Lead: {ai_data['title']} ({ai_data['price']}€)")
                    return ai_data
                else:
                    self.logger.error(f"IA Function Error ({response.status_code}): {response.text}")
                    # Si la IA falla, usamos un fallback básico de emergencia
                    return await self._fallback_parse(raw_content, source)

        except Exception as e:
            self.logger.error(f"AI Analysis failed: {e}")
            return None

    async def _fallback_parse(self, content: str, source: str) -> Optional[Dict[str, Any]]:
        """Emergency regex parsing if LLM fails"""
        content_lower = content.lower()
        if not any(kw in content_lower for kw in ['piso', 'casa', 'vivienda', 'alquiler']):
            return None
            
        content_hash = hashlib.md5(content.encode()).hexdigest()[:10]
        return {
            "external_id": f"{source[:2].upper()}-{content_hash}",
            "title": "Oportunidad detectada (AI Offline)",
            "description": content,
            "price": 0,
            "city": "Málaga",
            "source": source
        }
