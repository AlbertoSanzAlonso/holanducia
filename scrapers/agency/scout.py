import json
import logging
from typing import Any, Dict, List

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

    async def extract_posts_from_text(self, page_text: str, source: str = "Facebook") -> List[Dict[str, Any]]:
        if not self.llm_key:
            logger.error("Scout: falta GROQ_API_KEY u OPENAI_API_KEY.")
            return []

        prompt = f"""Analiza este texto crudo de un grupo de {source}.
Identifica cada publicación/post individual del feed del grupo.
Ignora menús, navegación, botones, sugerencias de amigos y metadatos de UI.

Devuelve SOLO un JSON array de objetos. Cada objeto:
- "text": texto completo del post (obligatorio)
- "url": enlace directo al post si aparece en el texto (opcional, string vacío si no lo encuentras)

Ejemplo:
[{{"text": "Se vende piso en...", "url": "https://www.facebook.com/groups/.../posts/..."}}]

Si no hay posts, devuelve [].

Texto:
{page_text[:15000]}
"""
        result = await self._call_ai_json(prompt)
        posts = self._parse_posts(result)
        logger.info("Scout: parseados %s posts estructurados de IA", len(posts))
        return posts

    def _parse_posts(self, result: Any) -> List[Dict[str, Any]]:
        raw_items: List[Any] = []
        if isinstance(result, list):
            raw_items = result
        elif isinstance(result, dict):
            raw_items = result.get("posts", result.get("items", []))
        if not isinstance(raw_items, list):
            return []

        out: List[Dict[str, Any]] = []
        for item in raw_items:
            if isinstance(item, str):
                text = item.strip()
                if len(text) < 40:
                    continue
                out.append({"text": text, "url": ""})
            elif isinstance(item, dict):
                text = (item.get("text") or item.get("raw_text") or "").strip()
                if len(text) < 40:
                    continue
                url = (item.get("url") or "").strip()
                out.append({"text": text, "url": url})
        return out

    async def _call_ai_json(self, prompt: str) -> Any:
        from scrapers.agency.llm_client import chat_completion

        content = await chat_completion(
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            timeout=60.0,
        )
        if not content:
            return None

        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return json.loads(content)
        except Exception as e:
            logger.error("Scout: error parseando IA: %s", e)
            return None
