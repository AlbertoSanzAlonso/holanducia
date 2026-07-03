"""Contexto de sync diario compartido entre scrapers y pipeline."""
from contextvars import ContextVar
from typing import Any, Dict, Optional, Set

sync_mode: ContextVar[bool] = ContextVar("sync_mode", default=False)


class SyncSession:
    """Registra URLs vistas durante un run de sync para reconciliar al final."""

    def __init__(self, sync_run_id: int, sources: Optional[list[str]] = None):
        self.sync_run_id = sync_run_id
        self.sources = sources or []
        self.seen_urls: Set[str] = set()
        self.stats: Dict[str, int] = {
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "deactivated": 0,
        }

    def record_seen(self, url: str) -> None:
        if url:
            self.seen_urls.add(url)

    def bump(self, key: str, n: int = 1) -> None:
        self.stats[key] = self.stats.get(key, 0) + n


sync_session: ContextVar[Optional[SyncSession]] = ContextVar("sync_session", default=None)


def is_sync_mode() -> bool:
    return sync_mode.get()


def get_sync_session() -> Optional[SyncSession]:
    return sync_session.get()
