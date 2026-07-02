import json
import logging
from typing import Any, Dict, List

import httpx

from scrapers.agency.analyst import AnalystAgent

logger = logging.getLogger(__name__)


class ScoutAgent(AnalystAgent):
    """Explora páginas difíciles: diagnostica bloqueos y extrae posts vía IA cuando falla el DOM."""

    async def diagnose_page(self, page_text: str, url: str) -> Dict[str, Any]:
        if not self.llm_key:
            return {"status": "unknown", "message": "Sin API key de IA", "posts_visible": False}

        prompt = f"""Diagnostica el estado de esta página de Facebook.
URL: {url}

Devuelve SOLO un JSON:
{{
    "status": "ok|login_required|join_required|blocked|empty|unknown",
    "message": "explicación breve en español",
    "posts_visible": true/false
}}

Indicadores:
- login_required: pide email/contraseña, "Log in", "Iniciar sesión"
- join_required: "Join group", "Unirse al grupo", "Solicitar unirse"
- blocked: checkpoint, captcha, "temporarily blocked", verificación
- empty: grupo accesible pero sin publicaciones visibles
- ok: hay publicaciones de usuarios en el feed

Texto de la página:
{page_text[:4000]}
"""
        result = await self._call_ai_json(prompt)
        if not result:
            return {"status": "unknown", "message": "No se pudo diagnosticar", "posts_visible": False}
        return result

    async def extract_posts_from_text(self, page_text: str, source: str = "Facebook") -> List[str]:
        if not self.llm_key:
            logger.error("Scout: falta GROQ_API_KEY u OPENAI_API_KEY.")
            return []

        prompt = f"""Analiza este texto crudo de un grupo de {source}.
Identifica cada publicación/post individual del feed del grupo.
Ignora menús, navegación, botones, sugerencias de amigos y metadatos de UI.

Devuelve SOLO un JSON array de strings. Cada string = texto completo de un post.
Si no hay posts, devuelve [].

Texto:
{page_text[:15000]}
"""
        result = await self._call_ai_json(prompt)
        if isinstance(result, list):
            return [p.strip() for p in result if isinstance(p, str) and len(p.strip()) > 40]
        if isinstance(result, dict):
            posts = result.get("posts", [])
            return [p.strip() for p in posts if isinstance(p, str) and len(p.strip()) > 40]
        return []

    async def _call_ai_json(self, prompt: str) -> Any:
        headers = {"Authorization": f"Bearer {self.llm_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.llm_url, json=payload, headers=headers)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]

                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                return json.loads(content)
        except Exception as e:
            logger.error("Scout: error en llamada IA: %s", e)
            return None
