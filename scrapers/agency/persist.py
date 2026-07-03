"""Persistencia unificada: Postgres (API) + embedding vectorial + sync diario."""
import logging
from typing import Any, Callable, Coroutine, Dict, Optional

from scrapers.agency.curator import CuratorAgent, make_lead_dedup_key
from scrapers.agency.supervisor import SupervisorAgent
from scrapers.agency.types import CurateAction
from scrapers.db_connector import DatabaseConnector
from scrapers.portal_utils import external_id_from_url, is_facebook_post_url, resolve_lead_identity
from scrapers.sync_context import get_sync_session
from scrapers.sync_utils import content_hash
from scrapers.fb_image_storage import download_facebook_images

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
    updated = 0
    unchanged = 0
    rejected_supervisor = 0
    raw_text_by_key = raw_text_by_key or {}
    session = get_sync_session()

    for lead in leads:
        if saved + updated + unchanged >= limit and not session:
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
        lead["content_hash"] = content_hash(lead)

        if source == "Facebook" and lead.get("images"):
            image_key = url or external_id or lead.get("title", "fb")
            hosted = await download_facebook_images(lead["images"], image_key)
            if hosted:
                lead["images"] = hosted
            elif not lead.get("price") and not lead.get("rooms"):
                skipped += 1
                logger.info("FB rechazado: sin foto descargable — %s", lead.get("title"))
                continue

        decision = await curator.evaluate_lead(lead, url=url, dedup_key=dedup_key)
        action = decision["action"]

        if action == CurateAction.UPDATE.value:
            existing = await connector.get_property_by_url(url)
            if existing and existing.get("content_hash") == lead["content_hash"]:
                unchanged += 1
                if session:
                    session.record_seen(url)
                    session.bump("unchanged")
                await mark_as_scraped(url)
                logger.debug("Sync sin cambios: %s", url)
                continue

            if await connector.upsert_property_with_embedding(lead):
                updated += 1
                if session:
                    session.record_seen(url)
                    session.bump("updated")
                await mark_as_scraped(url)
                logger.info("Sync actualizado: %s", lead.get("title"))
            else:
                skipped += 1
            continue

        if action != CurateAction.NEW.value:
            skipped += 1
            logger.debug("Curator descartó lead (%s): %s", decision["reason"], url)
            continue

        if await connector.upsert_property_with_embedding(lead):
            saved += 1
            if session:
                session.record_seen(url)
                session.bump("created")
            await mark_as_scraped(url)
            if raw_key:
                await mark_as_scraped(raw_key)
            logger.info("Persist [Postgres+vector]: %s", lead.get("title"))
        else:
            skipped += 1

    stats = {
        "saved": saved,
        "updated": updated,
        "unchanged": unchanged,
        "duplicates": skipped,
        "rejected_supervisor": rejected_supervisor,
        "created": saved,
    }
    return saved + updated, skipped, stats
