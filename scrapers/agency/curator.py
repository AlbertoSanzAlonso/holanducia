import hashlib
import logging
import os
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from scrapers.agency.types import CurateAction, CurateResult, RawLead
from scrapers.db_connector import DatabaseConnector

logger = logging.getLogger(__name__)

DedupCheckFn = Callable[[str], Coroutine[Any, Any, bool]]

DUPLICATE_THRESHOLD = float(os.getenv("VECTOR_DUPLICATE_THRESHOLD", "0.92"))


def make_dedup_key(text: str, prefix: str = "raw") -> str:
    digest = hashlib.md5(text[:500].encode()).hexdigest()[:12]
    return f"{prefix}-{digest}"


def make_lead_dedup_key(title: str, price: Any) -> str:
    digest = hashlib.md5(f"{title}{price}".encode()).hexdigest()[:12]
    return digest


class CuratorAgent:
    """Filtra candidatos antes de gastar IA o escribir en BD."""

    def __init__(
        self,
        connector: DatabaseConnector,
        is_already_scraped: DedupCheckFn,
    ):
        self.connector = connector
        self.is_already_scraped = is_already_scraped
        self._known_urls: Optional[Set[str]] = None
        self._known_external_ids: Optional[Set[str]] = None

    async def load_db_index(self) -> None:
        if self._known_urls is not None:
            return
        self._known_urls, self._known_external_ids = await self.connector.get_property_index()
        logger.info(
            "Curator: índice BD cargado (%s urls, %s external_ids)",
            len(self._known_urls),
            len(self._known_external_ids),
        )

    async def evaluate_raw(
        self,
        raw_text: str,
        *,
        source: str,
        base_url: str,
    ) -> CurateResult:
        dedup_key = make_dedup_key(raw_text)
        if await self.is_already_scraped(dedup_key):
            return {
                "action": CurateAction.DUPLICATE.value,
                "raw_lead": {
                    "source": source,
                    "raw_text": raw_text,
                    "dedup_key": dedup_key,
                    "base_url": base_url,
                },
                "reason": "redis_raw_hash",
            }

        return {
            "action": CurateAction.NEW.value,
            "raw_lead": {
                "source": source,
                "raw_text": raw_text,
                "dedup_key": dedup_key,
                "base_url": base_url,
            },
            "reason": "new_candidate",
        }

    async def evaluate_lead(
        self,
        lead: Dict[str, Any],
        *,
        url: str,
        dedup_key: str,
    ) -> CurateResult:
        await self.load_db_index()

        if await self.is_already_scraped(dedup_key):
            return {
                "action": CurateAction.DUPLICATE.value,
                "raw_lead": {"url": url, "dedup_key": dedup_key},
                "reason": "redis_lead_hash",
            }

        if url in (self._known_urls or set()):
            return {
                "action": CurateAction.DUPLICATE.value,
                "raw_lead": {"url": url, "dedup_key": dedup_key},
                "reason": "db_url_match",
            }

        external_id = lead.get("external_id")
        if external_id and external_id in (self._known_external_ids or set()):
            return {
                "action": CurateAction.DUPLICATE.value,
                "raw_lead": {"url": url, "dedup_key": dedup_key},
                "reason": "db_external_id_match",
            }

        similar = await self.connector.find_similar_property(lead, exclude_url=url)
        if similar:
            similarity = float(similar.get("similarity") or 0)
            if similarity >= DUPLICATE_THRESHOLD:
                logger.info(
                    "Curator [vector]: duplicado semántico (%.2f) — %s ≈ %s",
                    similarity,
                    lead.get("title"),
                    similar.get("title"),
                )
                return {
                    "action": CurateAction.DUPLICATE.value,
                    "raw_lead": {"url": url, "dedup_key": dedup_key},
                    "reason": f"vector_semantic_{similarity:.2f}",
                }

        return {
            "action": CurateAction.NEW.value,
            "raw_lead": {"url": url, "dedup_key": dedup_key},
            "reason": "new_lead",
        }

    async def curate_batch(
        self,
        raw_texts: List[str],
        *,
        source: str,
        base_url: str,
    ) -> tuple[List[RawLead], int]:
        approved: List[RawLead] = []
        skipped = 0

        for text in raw_texts:
            result = await self.evaluate_raw(text, source=source, base_url=base_url)
            if result["action"] == CurateAction.NEW.value:
                approved.append(result["raw_lead"])
            else:
                skipped += 1
                logger.debug("Curator descartó raw (%s): %s", result["reason"], result["raw_lead"]["dedup_key"])

        logger.info(
            "Curator [raw]: %s aprobados, %s duplicados de %s candidatos",
            len(approved),
            skipped,
            len(raw_texts),
        )
        return approved, skipped
