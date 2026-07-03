import hashlib
import os
from typing import Any, Dict, List, Optional

import httpx

EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = 1536


def property_to_embed_text(data: Dict[str, Any]) -> str:
    parts = [
        data.get("title"),
        f"Precio: {data.get('price')} EUR" if data.get("price") else None,
        f"Ciudad: {data.get('city')}" if data.get("city") else None,
        f"Barrio: {data.get('neighborhood')}" if data.get("neighborhood") else None,
        f"{data.get('rooms')} habitaciones" if data.get("rooms") else None,
        f"{data.get('size_m2')} m2" if data.get("size_m2") else None,
        data.get("description"),
        f"Fuente: {data.get('source')}" if data.get("source") else None,
    ]
    return " | ".join(str(p) for p in parts if p)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class EmbeddingService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/embeddings"

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    async def embed_text(self, text: str) -> Optional[List[float]]:
        if not self.api_key or not text.strip():
            return None

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.api_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": EMBEDDING_MODEL, "input": text[:8000]},
            )
            response.raise_for_status()
            data = response.json()["data"][0]["embedding"]
            return data

    async def embed_property(self, prop: Dict[str, Any]) -> Optional[tuple[str, List[float]]]:
        text = property_to_embed_text(prop)
        if not text.strip():
            return None
        vector = await self.embed_text(text)
        if not vector:
            return None
        return content_hash(text), vector
