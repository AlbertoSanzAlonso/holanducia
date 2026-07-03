import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Property, SyncRun

logger = logging.getLogger(__name__)


def compute_content_hash(data: dict) -> str:
    payload = {
        "title": data.get("title"),
        "price": data.get("price"),
        "city": data.get("city"),
        "neighborhood": data.get("neighborhood"),
        "size_m2": data.get("size_m2"),
        "rooms": data.get("rooms"),
        "bathrooms": data.get("bathrooms"),
        "description": (data.get("description") or "")[:500],
        "images": (data.get("images") or [])[:3],
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class SyncService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_run(self, sources: list[str]) -> SyncRun:
        run = SyncRun(status="running", sources=sources, stats={})
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def touch_seen(self, url: str, *, content_hash: Optional[str] = None) -> None:
        now = datetime.now(timezone.utc)
        values: Dict[str, Any] = {"last_seen_at": now, "is_active": True}
        if content_hash:
            values["content_hash"] = content_hash
        await self.db.execute(
            update(Property).where(Property.url == url).values(**values)
        )
        await self.db.commit()

    async def finalize_run(
        self,
        run_id: int,
        *,
        seen_urls: set[str],
        sources: list[str],
        stats: dict,
    ) -> dict:
        now = datetime.now(timezone.utc)
        deactivated = 0
        min_coverage = float(os.getenv("SYNC_DEACTIVATE_MIN_COVERAGE", "0.25"))

        if seen_urls and sources:
            for source in sources:
                active_result = await self.db.execute(
                    select(Property).where(
                        Property.source == source,
                        Property.is_active.is_(True),
                    )
                )
                active_props = active_result.scalars().all()
                if not active_props:
                    continue

                active_urls = {p.url for p in active_props}
                seen_in_source = seen_urls & active_urls
                coverage = len(seen_in_source) / len(active_urls) if active_urls else 0

                if coverage < min_coverage and len(seen_urls) < len(active_urls):
                    logger.warning(
                        "Sync: omitiendo bajas en %s (cobertura %.0f%%, %s/%s)",
                        source,
                        coverage * 100,
                        len(seen_in_source),
                        len(active_urls),
                    )
                    continue

                for prop in active_props:
                    if prop.url not in seen_urls:
                        prop.is_active = False
                        prop.updated_at = now
                        deactivated += 1

        run = await self.db.get(SyncRun, run_id)
        if run:
            run.status = "completed"
            run.completed_at = now
            run.stats = {**stats, "deactivated": deactivated}
            await self.db.commit()

        return {"deactivated": deactivated, **stats}

    async def get_by_url(self, url: str) -> Optional[Property]:
        result = await self.db.execute(select(Property).where(Property.url == url))
        return result.scalar_one_or_none()
