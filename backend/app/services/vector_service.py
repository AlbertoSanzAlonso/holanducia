import os
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Property
from backend.app.services.embedding_service import EmbeddingService, property_to_embed_text

logger = logging.getLogger(__name__)


def _vector_literal(values: List[float]) -> str:
    return "[" + ",".join(str(v) for v in values) + "]"


class VectorService:
    DUPLICATE_THRESHOLD = float(os.getenv("VECTOR_DUPLICATE_THRESHOLD", "0.92"))
    UPDATE_THRESHOLD = float(os.getenv("VECTOR_UPDATE_THRESHOLD", "0.75"))

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedder = EmbeddingService()

    async def upsert_property_embedding(self, prop: Property) -> bool:
        if not self.embedder.available:
            return False

        prop_dict = {
            "title": prop.title,
            "price": prop.price,
            "city": prop.city,
            "neighborhood": prop.neighborhood,
            "rooms": prop.rooms,
            "size_m2": prop.size_m2,
            "description": prop.description,
            "source": prop.source,
        }
        result = await self.embedder.embed_property(prop_dict)
        if not result:
            return False

        content_hash, vector = result
        literal = _vector_literal(vector)

        try:
            await self.db.execute(
                text(
                    """
                    INSERT INTO property_embeddings (property_id, content_hash, embedding)
                    VALUES (:property_id, :content_hash, CAST(:embedding AS vector))
                    ON CONFLICT (property_id) DO UPDATE SET
                        content_hash = EXCLUDED.content_hash,
                        embedding = EXCLUDED.embedding,
                        embedded_at = NOW()
                    """
                ),
                {"property_id": prop.id, "content_hash": content_hash, "embedding": literal},
            )
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            logger.exception("Error guardando embedding property #%s: %s", prop.id, e)
            return False

    async def find_similar(
        self,
        query_text: str,
        *,
        limit: int = 5,
        min_similarity: float = 0.75,
    ) -> List[Dict[str, Any]]:
        if not self.embedder.available or not query_text.strip():
            return []

        vector = await self.embedder.embed_text(query_text)
        if not vector:
            return []

        literal = _vector_literal(vector)
        result = await self.db.execute(
            text(
                """
                SELECT
                    p.id,
                    p.url,
                    p.title,
                    p.price,
                    p.city,
                    1 - (pe.embedding <=> CAST(:query AS vector)) AS similarity
                FROM property_embeddings pe
                JOIN properties p ON p.id = pe.property_id
                WHERE 1 - (pe.embedding <=> CAST(:query AS vector)) >= :min_similarity
                ORDER BY pe.embedding <=> CAST(:query AS vector)
                LIMIT :limit
                """
            ),
            {"query": literal, "min_similarity": min_similarity, "limit": limit},
        )
        rows = result.mappings().all()
        return [dict(row) for row in rows]

    async def find_similar_property(
        self,
        prop_data: Dict[str, Any],
        *,
        exclude_url: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        matches = await self.find_similar(
            property_to_embed_text(prop_data),
            limit=3,
            min_similarity=self.UPDATE_THRESHOLD,
        )
        for match in matches:
            if exclude_url and match.get("url") == exclude_url:
                continue
            return match
        return None

    async def backfill_missing(self, limit: int = 100) -> int:
        if not self.embedder.available:
            return 0

        result = await self.db.execute(
            text(
                """
                SELECT p.id
                FROM properties p
                LEFT JOIN property_embeddings pe ON pe.property_id = p.id
                WHERE p.is_active = TRUE AND pe.id IS NULL
                ORDER BY p.created_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
        ids = [row[0] for row in result.fetchall()]
        embedded = 0

        for prop_id in ids:
            prop = await self.db.get(Property, prop_id)
            if prop and await self.upsert_property_embedding(prop):
                embedded += 1

        return embedded
