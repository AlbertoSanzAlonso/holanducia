import logging
import httpx
import json
import hashlib
import os
import re
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class AnalystAgent:
    def __init__(self):
        self.groq_key = os.environ.get("GROQ_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        if self.groq_key:
            self.llm_url = "https://api.groq.com/openai/v1/chat/completions"
            self.llm_key = self.groq_key
            self.llm_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
        elif self.openai_key:
            self.llm_url = "https://api.openai.com/v1/chat/completions"
            self.llm_key = self.openai_key
            self.llm_model = "gpt-4o-mini"
        else:
            self.llm_url = None
            self.llm_key = None
            self.llm_model = None

    async def parse_raw_text(
        self,
        raw_content: str,
        source: str = "Facebook",
        *,
        prequalified: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Analiza un anuncio individual y extrae datos estructurados"""
        self.logger = logger
        self.logger.info(f"🧠 AI Analizando post individual de {source}...")

        prequalified_note = ""
        if prequalified:
            prequalified_note = """
        NOTA: Post de grupo Facebook inmobiliario. Extrae datos SOLO si es un anuncio de vivienda.
        is_real_estate=false si es: productos, servicios, restaurantes, empleo, conversación general, spam.
        is_real_estate=true SOLO si ofrece/busca/alquila/vende una vivienda o local.
        """

        prompt = f"""
        Actúa como un experto buscador de inversiones inmobiliarias. 
        Analiza el siguiente texto de {source} y extrae los datos de la propiedad.
        {prequalified_note}
        REGLAS DE ORO:
        1. TÍTULO: Profesional, específico (zona + tipo + habitaciones). NUNCA genérico tipo "Propiedad en X".
        2. PRECIO: Número en euros del anuncio. Si no hay precio explícito, pon 0 (no inventes).
        3. CIUDAD/BARRIO: Extrae del texto; si no hay ciudad clara, null (no asumas Málaga).
        4. DESCRIPTION: Texto completo del anuncio con m², planta, extras, contacto. Copia el post literalmente.
        5. size_m2, rooms, bathrooms: extrae solo si aparecen explícitamente (null si no).

        Devuelve SOLO un JSON:
        {{
            "title": "título profesional",
            "price": número,
            "city": "ciudad o null",
            "neighborhood": "barrio o null",
            "description": "descripción completa del post",
            "rooms": número o null,
            "bathrooms": número o null,
            "size_m2": número o null,
            "images": [],
            "is_individual": true/false,
            "is_real_estate": true/false
        }}

        Texto: {raw_content[:3500]}
        """

        return await self._call_ai(prompt, source, prequalified=prequalified)

    async def parse_bulk_text(
        self,
        raw_text: str,
        source: str,
        page_images: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Analiza un listado masivo (Modo Sniper)"""
        from scrapers.image_utils import assign_images_to_leads

        logger.info(f"🧠 AI Bulk Extraction: Procesando listado masivo de {source}...")

        image_hint = ""
        if page_images:
            image_hint = f"\nURLs de fotos detectadas en la página (asigna la que corresponda a cada anuncio): {page_images[:40]}"

        prompt = f"""
        Analiza este listado de {source} y extrae TODAS las propiedades.
        Devuelve un array JSON de objetos con: title, price, city, description, rooms, url (enlace directo al anuncio si aparece), images (array de URLs de foto).
        Si el título falta, créalo tú. Si el precio falta, pon 0. Si no hay foto clara, usa [].
        {image_hint}

        Texto: {raw_text[:12000]}
        """

        result = await self._call_ai(prompt, source, is_bulk=True)
        leads = result if isinstance(result, list) else []
        assign_images_to_leads(leads, page_images or [])
        return leads

    async def _call_ai(self, prompt: str, source: str, is_bulk=False, prequalified: bool = False):
        """Llamada genérica a OpenAI o Groq (compatible OpenAI)."""
        if not self.llm_key:
            logger.error("❌ Falta GROQ_API_KEY u OPENAI_API_KEY para el análisis IA.")
            return [] if is_bulk else None

        headers = {"Authorization": f"Bearer {self.llm_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.llm_model,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.llm_url, json=payload, headers=headers)
                response.raise_for_status()
                content = response.json()['choices'][0]['message']['content']
                
                # Limpieza de markdown
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                
                data = json.loads(content)
                
                if not is_bulk:
                    if not data.get("is_real_estate", True):
                        logger.warning("🚫 Clasificado como NO inmobiliario por IA.")
                        return None
                    # Asegurar título
                    if not data.get("title") or data["title"] == "None":
                        city = data.get("city") or "Málaga"
                        data["title"] = f"Propiedad en {city}"
                    if not data.get("city"):
                        data["city"] = "Málaga"
                    data["price"] = self._clean_price(data.get("price"))
                    if not isinstance(data.get("images"), list):
                        data["images"] = []
                    data["source"] = source
                    return data
                else:
                    leads = data.get("properties", data) if isinstance(data, dict) else data
                    # Saneamiento de leads masivos
                    for l in leads:
                        l["source"] = source
                        l["price"] = self._clean_price(l.get("price"))
                        if not isinstance(l.get("images"), list):
                            l["images"] = []
                    return leads
        except Exception as e:
            logger.error(f"❌ Error en llamada AI: {e}")
            return [] if is_bulk else None

    def _clean_price(self, price_val):
        try:
            if isinstance(price_val, str):
                price_val = re.sub(r'[^\d.]', '', price_val)
            return float(price_val)
        except:
            return 0
