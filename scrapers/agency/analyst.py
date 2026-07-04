import logging
import json
import re
from typing import Optional, Dict, Any, List

from scrapers.agency.llm_client import chat_completion, has_llm_key

logger = logging.getLogger(__name__)

class AnalystAgent:
    def __init__(self):
        self.llm_key = has_llm_key()

    async def parse_portal_detail(
        self,
        raw_content: str,
        source: str,
        *,
        url: str = "",
        pre_parsed: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Analiza ficha completa de portal con criterio de inversor; usa parser + IA."""
        logger.info("🧠 Analyst portal detail: %s", url or source)

        base = dict(pre_parsed or {})
        base.pop("_parse_meta", None)

        prompt = f"""
Eres analista inmobiliario senior. Refina y completa los datos de ESTA FICHA INDIVIDUAL de {source}.
URL: {url}

REGLAS ESTRICTAS:
1. TÍTULO: tipo de inmueble + zona (ej. "Chalet adosado en Caleta de Vélez, 4 hab."). NUNCA incluyas "41 fotos", "tour", "oportunidad", botones web.
2. PRECIO: solo el precio de venta/alquiler en euros. Si no aparece, 0.
3. size_m2: SOLO superficie construida o útil en m². NUNCA uses antigüedad ("20-30 años"), plantas, ni número de fotos.
4. rooms / bathrooms: habitaciones y baños completos del anuncio.
5. city: municipio. neighborhood: barrio/urbanización si aparece.
6. description: texto limpio de la descripción del inmueble + características relevantes (piscina, terraza, garaje, placas solares, licencia turística). Sin legal boilerplate ni publicidad de la inmobiliaria.
7. has_parking, has_terrace, has_pool: true/false según el anuncio.
8. is_individual: true si es particular, false si es inmobiliaria/profesional.
9. catastro_ref: referencia del anuncio si existe (ej. "000018").
10. year_built: solo si hay año numérico claro; si dice "20-30 años" deja null.

Datos pre-extraídos (puedes corregirlos):
{json.dumps({k: v for k, v in base.items() if k in {"title","price","city","neighborhood","size_m2","rooms","bathrooms","description","has_parking","has_terrace","has_pool","is_individual","catastro_ref"}}, ensure_ascii=False)[:3000]}

Texto de la ficha:
{(raw_content or "")[:14000]}

Devuelve SOLO JSON:
{{
  "title": "...",
  "price": número,
  "city": "... o null",
  "neighborhood": "... o null",
  "description": "...",
  "rooms": número o null,
  "bathrooms": número o null,
  "size_m2": número o null,
  "has_parking": true/false,
  "has_terrace": true/false,
  "has_pool": true/false,
  "is_individual": true/false,
  "catastro_ref": "... o null",
  "year_built": número o null,
  "images": [],
  "is_real_estate": true
}}
"""
        result = await self._call_ai(
            prompt, source, prequalified=False, raw_content=raw_content, is_portal=True
        )
        if not result:
            if base.get("title") and (base.get("price") or base.get("size_m2")):
                base["is_real_estate"] = True
                base["source"] = source
                base["price"] = self._clean_price(base.get("price"))
                return base
            return None

        for key, val in base.items():
            if key in ("images", "url", "source"):
                continue
            if result.get(key) in (None, "", 0) and val not in (None, "", 0):
                result[key] = val

        if pre_parsed and pre_parsed.get("images") and not result.get("images"):
            result["images"] = pre_parsed["images"]
        if url and not result.get("url"):
            result["url"] = url

        return result

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

        return await self._call_ai(prompt, source, prequalified=prequalified, raw_content=raw_content)

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

    async def _call_ai(
        self,
        prompt: str,
        source: str,
        is_bulk=False,
        prequalified: bool = False,
        raw_content: str = "",
        is_portal: bool = False,
    ):
        """Llamada genérica a OpenAI o Groq (compatible OpenAI)."""
        if not self.llm_key:
            logger.error("❌ Falta GROQ_API_KEY u OPENAI_API_KEY para el análisis IA.")
            return [] if is_bulk else None

        content = await chat_completion([{"role": "user", "content": prompt}])
        if not content:
            return [] if is_bulk else None

        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)

            if not is_bulk:
                if not data.get("is_real_estate", True):
                    logger.warning("🚫 Clasificado como NO inmobiliario por IA.")
                    return None
                if not data.get("title") or data["title"] in ("None", "null"):
                    first_line = (raw_content.split("\n")[0] if prequalified else "").strip()
                    data["title"] = (first_line[:120] if len(first_line) > 15 else None) or "Anuncio inmobiliario"
                if prequalified and not data.get("city"):
                    data["city"] = None
                elif not data.get("city") and not is_portal:
                    data["city"] = "Málaga"
                data["price"] = self._clean_price(data.get("price"))
                if not isinstance(data.get("images"), list):
                    data["images"] = []
                data["source"] = source
                if data.get("is_individual") is False:
                    data["is_agency"] = True
                elif data.get("is_individual") is True:
                    data["is_agency"] = False
                for bool_field in ("has_parking", "has_terrace", "has_pool"):
                    if bool_field in data:
                        data[bool_field] = bool(data[bool_field])
                return data

            leads = data.get("properties", data) if isinstance(data, dict) else data
            for l in leads:
                l["source"] = source
                l["price"] = self._clean_price(l.get("price"))
                if not isinstance(l.get("images"), list):
                    l["images"] = []
            return leads
        except Exception as e:
            logger.error(f"❌ Error parseando respuesta AI: {e}")
            return [] if is_bulk else None

    def _clean_price(self, price_val):
        try:
            if isinstance(price_val, str):
                price_val = re.sub(r'[^\d.]', '', price_val)
            return float(price_val)
        except:
            return 0
