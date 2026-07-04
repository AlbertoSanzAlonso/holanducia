"""Cliente LLM unificado: Groq/OpenAI con fallback, reintentos y límite de concurrencia."""
import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").lower().strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
LLM_MAX_CONCURRENT = int(os.getenv("LLM_MAX_CONCURRENT", "2"))
LLM_RETRY_MAX = int(os.getenv("LLM_RETRY_MAX", "2"))

_semaphore = asyncio.Semaphore(LLM_MAX_CONCURRENT)


@dataclass(frozen=True)
class LLMEndpoint:
    name: str
    url: str
    key: str
    model: str


def available_llm_providers() -> List[str]:
    names: List[str] = []
    if os.environ.get("GROQ_API_KEY"):
        names.append("groq")
    if os.environ.get("OPENAI_API_KEY"):
        names.append("openai")
    return names


def _build_endpoints() -> List[LLMEndpoint]:
    endpoints: List[LLMEndpoint] = []
    groq_key = os.environ.get("GROQ_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    if groq_key:
        endpoints.append(
            LLMEndpoint(
                "groq",
                "https://api.groq.com/openai/v1/chat/completions",
                groq_key,
                GROQ_MODEL,
            )
        )
    if openai_key:
        endpoints.append(
            LLMEndpoint(
                "openai",
                "https://api.openai.com/v1/chat/completions",
                openai_key,
                OPENAI_CHAT_MODEL,
            )
        )
    return endpoints


def ordered_llm_endpoints() -> List[LLMEndpoint]:
    endpoints = _build_endpoints()
    if not endpoints:
        return []

    if LLM_PROVIDER == "openai":
        preferred = [e for e in endpoints if e.name == "openai"]
        return preferred or endpoints
    if LLM_PROVIDER == "groq":
        preferred = [e for e in endpoints if e.name == "groq"]
        return preferred or endpoints

    groq = [e for e in endpoints if e.name == "groq"]
    openai = [e for e in endpoints if e.name == "openai"]
    return groq + openai


def has_llm_key() -> bool:
    return bool(_build_endpoints())


async def chat_completion(
    messages: List[Dict[str, str]],
    *,
    temperature: Optional[float] = None,
    timeout: float = 60.0,
) -> Optional[str]:
    """Llama al LLM configurado; en auto hace fallback Groq → OpenAI si hay 429."""
    endpoints = ordered_llm_endpoints()
    if not endpoints:
        logger.error("Falta GROQ_API_KEY u OPENAI_API_KEY para el análisis IA.")
        return None

    async with _semaphore:
        for ep in endpoints:
            for attempt in range(LLM_RETRY_MAX + 1):
                try:
                    payload: Dict[str, Any] = {"model": ep.model, "messages": messages}
                    if temperature is not None:
                        payload["temperature"] = temperature

                    async with httpx.AsyncClient(timeout=timeout) as client:
                        response = await client.post(
                            ep.url,
                            headers={
                                "Authorization": f"Bearer {ep.key}",
                                "Content-Type": "application/json",
                            },
                            json=payload,
                        )

                    if response.status_code == 429:
                        wait = min(2 ** attempt, 10)
                        logger.warning(
                            "LLM %s rate limit 429 (intento %s/%s) — espera %ss",
                            ep.name,
                            attempt + 1,
                            LLM_RETRY_MAX + 1,
                            wait,
                        )
                        if attempt < LLM_RETRY_MAX:
                            await asyncio.sleep(wait)
                            continue
                        break

                    if response.status_code in (503, 502):
                        logger.warning("LLM %s HTTP %s — siguiente proveedor", ep.name, response.status_code)
                        break

                    response.raise_for_status()
                    if ep.name == "openai" and endpoints[0].name != "openai":
                        logger.info("LLM fallback → OpenAI (%s)", OPENAI_CHAT_MODEL)
                    return response.json()["choices"][0]["message"]["content"]

                except httpx.HTTPStatusError as e:
                    code = e.response.status_code
                    if code in (429, 502, 503) and attempt < LLM_RETRY_MAX:
                        await asyncio.sleep(min(2 ** attempt, 10))
                        continue
                    logger.warning("LLM %s HTTP %s: %s", ep.name, code, e)
                    break
                except Exception as e:
                    logger.warning("LLM %s error: %s", ep.name, e)
                    break

    logger.error("Todas las llamadas LLM fallaron (revisa rate limits Groq o usa LLM_PROVIDER=openai)")
    return None
