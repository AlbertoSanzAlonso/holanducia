from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict


class CurateAction(str, Enum):
    NEW = "new"
    DUPLICATE = "duplicate"
    UPDATE = "update"
    SKIP = "skip"


class RawLead(TypedDict, total=False):
    source: str
    raw_text: str
    dedup_key: str
    url: str
    base_url: str
    metadata: Dict[str, Any]


class CurateResult(TypedDict):
    action: str
    raw_lead: RawLead
    reason: str


class PipelineStats(TypedDict, total=False):
    raw_in: int
    curated_out: int
    duplicates: int
    analyzed: int
    saved: int


class PropertyPipelineState(TypedDict, total=False):
    source: str
    base_url: str
    raw_candidates: List[str]
    approved: List[RawLead]
    leads: List[Dict[str, Any]]
    saved_count: int
    skipped_count: int
    limit: int
    stats: PipelineStats
    error: Optional[str]
