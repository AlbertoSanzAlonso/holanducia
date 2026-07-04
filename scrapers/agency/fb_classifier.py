"""Clasificador estricto de posts Facebook — ¿es anuncio inmobiliario?"""
import json
import logging
import os
from typing import Optional, TypedDict

from scrapers.agency.llm_client import chat_completion, has_llm_key
from scrapers.fb_utils import is_property_listing_text

logger = logging.getLogger(__name__)

MIN_CONFIDENCE = float(os.getenv("FB_CLASSIFIER_MIN_CONFIDENCE", "0.85"))


class ClassifyResult(TypedDict):
    is_listing: bool
    confidence: float
    reason: str


class FacebookClassifierAgent:
    """Primera línea de defensa: clasificación binaria estricta antes del Analyst."""

    def __init__(self):
        self.llm_key = has_llm_key()

    async def classify(self, text: str) -> ClassifyResult:
        if not is_property_listing_text(text):
            return {
                "is_listing": False,
                "confidence": 0.95,
                "reason": "heuristica_estricta_rechazado",
            }

        if not self.llm_key:
            return {
                "is_listing": is_property_listing_text(text),
                "confidence": 0.7,
                "reason": "solo_heuristica_sin_ia",
            }

        return await self._ai_classify(text)

    async def _ai_classify(self, text: str) -> ClassifyResult:
        prompt = f"""Eres un clasificador ESTRICTO de anuncios inmobiliarios en grupos de Facebook de España.

Tu única tarea: decidir si el texto es un ANUNCIO de compraventa o alquiler de VIVIENDA/LOCAL.

is_listing=TRUE solo si cumple TODAS:
1. Ofrece o busca una vivienda, piso, casa, chalet, estudio, local, garaje, terreno para uso residencial/comercial inmobiliario
2. Hay intención clara de venta, alquiler u oportunidad inmobiliaria
3. El texto principal trata de esa propiedad (no es comentario lateral)

is_listing=FALSE si es cualquiera de estos (ejemplos reales):
- Opiniones sobre productos, tiendas, restaurantes ("excelentes productos", "los recomiendo")
- Empleo, servicios, clases, eventos
- Conversación social, felicitaciones, memes
- Coches, muebles, electrodomésticos (no inmueble)
- Preguntas generales del grupo sin anuncio concreto
- Repost de noticias sin anuncio de piso/casa

Sé MUY conservador: ante duda → is_listing=false.

Texto del post:
{text[:2800]}

JSON estricto:
{{"is_listing": true/false, "confidence": 0.0-1.0, "reason": "motivo breve en español"}}"""

        try:
            content = await chat_completion(
                [{"role": "user", "content": prompt}],
                temperature=0.1,
                timeout=40.0,
            )
            if not content:
                raise RuntimeError("sin respuesta LLM")
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            data = json.loads(content)
            is_listing = bool(data.get("is_listing"))
            confidence = float(data.get("confidence") or 0)
            reason = str(data.get("reason") or "ia_classify")
            return {"is_listing": is_listing, "confidence": confidence, "reason": reason}
        except Exception as e:
            logger.warning("FacebookClassifier IA falló: %s", e)
            strict = is_property_listing_text(text)
            return {
                "is_listing": strict,
                "confidence": 0.6 if strict else 0.9,
                "reason": "fallback_heuristica",
            }

    def passes(self, result: ClassifyResult) -> bool:
        if not result["is_listing"]:
            return False
        return result["confidence"] >= MIN_CONFIDENCE
