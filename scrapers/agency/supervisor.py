"""Agente Supervisor — validación final antes de persistir en Postgres + vector."""
import json
import logging
import os
import re
from typing import Any, Dict, Optional, TypedDict

import httpx

from scrapers.fb_utils import is_property_listing_text, is_quality_facebook_lead
from scrapers.portal_utils import is_facebook_post_url, is_valid_listing_url

logger = logging.getLogger(__name__)

GENERIC_TITLE = re.compile(r"^propiedad en [a-záéíóúñ\s]+$", re.IGNORECASE)


class SuperviseResult(TypedDict):
    approved: bool
    reason: str
    quality_score: int


class SupervisorAgent:
    """Revisa cada anuncio individualmente antes de guardarlo."""

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

    async def review(
        self,
        lead: Dict[str, Any],
        *,
        source: str,
        raw_text: str = "",
    ) -> SuperviseResult:
        heuristic = self._heuristic_review(lead, source, raw_text)
        if not heuristic["approved"]:
            logger.info("Supervisor [heurística] rechazado: %s — %s", lead.get("title"), heuristic["reason"])
            return heuristic

        if self.llm_key:
            ai_result = await self._ai_review(lead, source, raw_text)
            if ai_result:
                if ai_result["approved"]:
                    logger.info("Supervisor [IA] aprobado: %s — %s", lead.get("title"), ai_result["reason"])
                else:
                    logger.info("Supervisor [IA] rechazado: %s — %s", lead.get("title"), ai_result["reason"])
                return ai_result

        logger.info("Supervisor [heurística] aprobado (sin IA): %s", lead.get("title"))
        return heuristic

    def _heuristic_review(self, lead: Dict[str, Any], source: str, raw_text: str) -> SuperviseResult:
        title = (lead.get("title") or "").strip()
        description = (lead.get("description") or "").strip()
        price = float(lead.get("price") or 0)
        rooms = lead.get("rooms")
        size_m2 = lead.get("size_m2")
        images = lead.get("images") or []
        url = lead.get("url") or ""
        context = raw_text or description

        if not title or title.lower() == "none":
            return {"approved": False, "reason": "sin_título", "quality_score": 0}

        if source == "Facebook":
            if not is_property_listing_text(context):
                return {"approved": False, "reason": "fb_no_inmobiliario", "quality_score": 0}
            if not is_quality_facebook_lead(lead, context, min_score=5):
                return {"approved": False, "reason": "fb_calidad_insuficiente", "quality_score": 1}
            if not self.llm_key:
                return {"approved": False, "reason": "fb_requiere_supervisor_ia", "quality_score": 0}
        else:
            if price <= 0 and not rooms and not size_m2:
                return {"approved": False, "reason": "sin_precio_ni_datos", "quality_score": 1}
            if GENERIC_TITLE.match(title) and price <= 0 and not images:
                return {"approved": False, "reason": "titulo_generico_sin_datos", "quality_score": 1}

        score = 0
        if price > 0:
            score += 2
        if rooms:
            score += 1
        if size_m2:
            score += 1
        if images:
            score += 2
        if is_valid_listing_url(url):
            score += 2
        if len(description) >= 80:
            score += 1

        min_score = 5 if source == "Facebook" else 2
        if score < min_score:
            return {"approved": False, "reason": f"score_bajo_{score}", "quality_score": score}

        return {"approved": True, "reason": "heurística_ok", "quality_score": score}

    async def _ai_review(self, lead: Dict[str, Any], source: str, raw_text: str) -> Optional[SuperviseResult]:
        context = raw_text or lead.get("description") or ""
        if source == "Facebook":
            prompt = f"""Eres el Supervisor INMOBILIARIO de HolanducIA. Clasificación ESTRICTA de posts de Facebook.

RECHAZAR (approved=false) sin excepción:
- Opiniones, recomendaciones de productos/tiendas ("excelentes", "recomiendo")
- Conversación social, agradecimientos, memes
- Empleo, servicios, coches, muebles
- Posts sin anuncio concreto de vivienda/local

APROBAR (approved=true) SOLO si:
- Anuncio claro de piso/casa/local en venta o alquiler
- Precio O (habitaciones + m²) O foto de la propiedad
- Texto describe una propiedad específica

Título: {lead.get("title")}
Precio: {lead.get("price")} EUR | Hab: {lead.get("rooms")} | m²: {lead.get("size_m2")}
Fotos descargadas: {len(lead.get("images") or [])}
URL post: {lead.get("url")}

Texto:
{context[:2500]}

JSON: {{"approved": true/false, "reason": "motivo", "quality_score": 0-10}}"""
        else:
            prompt = f"""
Eres el Supervisor de calidad de HolanducIA. Decides si un anuncio debe guardarse en la base de datos.

Fuente: {source}
Título: {lead.get("title")}
Precio: {lead.get("price")} EUR
Ciudad: {lead.get("city")}
Habitaciones: {lead.get("rooms")}
m²: {lead.get("size_m2")}
URL: {lead.get("url")}
Fotos: {len(lead.get("images") or [])}

Texto original:
{context[:2500]}

APROBAR (approved=true) SOLO si:
- Es un anuncio real de vivienda/local en venta o alquiler
- Tiene datos útiles (precio, habitaciones, m², foto o enlace verificable)
- NO es spam, productos, servicios, empleo ni conversación general

RECHAZAR si el texto no describe una propiedad inmobiliaria.

Devuelve SOLO JSON:
{{"approved": true/false, "reason": "motivo breve", "quality_score": 0-10}}
"""
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    self.llm_url,
                    headers={"Authorization": f"Bearer {self.llm_key}", "Content-Type": "application/json"},
                    json={"model": self.llm_model, "messages": [{"role": "user", "content": prompt}]},
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                data = json.loads(content)
                return {
                    "approved": bool(data.get("approved")),
                    "reason": str(data.get("reason") or "ia_review"),
                    "quality_score": int(data.get("quality_score") or 0),
                }
        except Exception as e:
            logger.warning("Supervisor IA falló, usando heurística: %s", e)
            return None
