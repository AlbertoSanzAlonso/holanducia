"""Persistencia unificada: Postgres (API) + embedding vectorial."""
import logging
from typing import Any, Callable, Coroutine, Dict, Optional

from scrapers.agency.curator import CuratorAgent, make_lead_dedup_key
from scrapers.agency.supervisor import SupervisorAgent
from scrapers.agency.types import CurateAction
from scrapers.db_connector import DatabaseConnector
from scrapers.portal_utils import external_id_from_url, is_facebook_post_url, resolve_lead_identity

logger = logging.getLogger(__name__)

PersistFn = Callable[[Dict[str, Any], str], Coroutine[Any, Any, bool]]
MarkScrapedFn = Callable[[str], Coroutine[Any, Any, None]]


async def persist_supervised_leads(
    leads: list[Dict[str, Any]],
    *,
    source: str,
    base_url: str,
    limit: int,
    connector: DatabaseConnector,
    curator: CuratorAgent,
    supervisor: SupervisorAgent,
    persist_lead: PersistFn,
    mark_as_scraped: MarkScrapedFn,
    raw_text_by_key: Optional[Dict[str, str]] = None,
    skipped: int = 0,
) -> tuple[int, int, Dict[str, int]]:
    saved = 0
    rejected_supervisor = 0
    raw_text_by_key = raw_text_by_key or {}

    for lead in leads:
        if saved >= limit:
            break

        lead = dict(lead)
        raw_key = lead.pop("_raw_dedup_key", None)
        raw_text = raw_text_by_key.get(raw_key or "", lead.get("description") or "")

        review = await supervisor.review(lead, source=source, raw_text=raw_text)
        if not review["approved"]:
            rejected_supervisor += 1
            skipped += 1
            continue

        candidate_url = lead.get("url") or ""
        if candidate_url and is_facebook_post_url(candidate_url):
            dedup_key = external_id_from_url(candidate_url)
        else:
            dedup_key = make_lead_dedup_key(lead.get("title", ""), lead.get("price", 0))

        url, external_id = resolve_lead_identity(lead, base_url)
        lead["external_id"] = external_id
        lead["url"] = url
        lead["source"] = source

        decision = await curator.evaluate_lead(lead, url=url, dedup_key=dedup_key)
        if decision["action"] != CurateAction.NEW.value:
            skipped += 1
            logger.debug("Curator descartó lead (%s): %s", decision["reason"], url)
            continue

        if await connector.upsert_property_with_embedding(lead):
            saved += 1
            await mark_as_scraped(url)
            if raw_key:
                await mark_as_scraped(raw_key)
            logger.info(
                "Persist [Postgres+vector]: %s (score=%s)",
                lead.get("title"),
                review.get("quality_score"),
            )
        else:
            skipped += 1
            logger.error("Fallo persistencia: %s", lead.get("title"))

    stats = {
        "saved": saved,
        "duplicates": skipped,
        "rejected_supervisor": rejected_supervisor,
    }
    return saved, skipped, stats
