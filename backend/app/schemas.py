from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str


class PropertyBase(BaseModel):
    external_id: Optional[str] = None
    url: str
    source: Optional[str] = None
    title: Optional[str] = None
    price: float = 0
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    address: Optional[str] = None
    size_m2: Optional[float] = None
    rooms: Optional[int] = None
    bathrooms: Optional[int] = None
    has_parking: bool = False
    has_terrace: bool = False
    has_pool: bool = False
    has_garden: bool = False
    has_trastero: bool = False
    garage_spots: Optional[int] = None
    floor: Optional[int] = None
    is_individual: bool = False
    is_agency: bool = True
    description: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    opportunity_score: int = 0
    opportunity_reasons: List[str] = Field(default_factory=list)
    category_id: Optional[int] = None
    catastro_ref: Optional[str] = None
    year_built: Optional[int] = None
    is_active: bool = True
    last_seen_at: Optional[datetime] = None
    content_hash: Optional[str] = None


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    external_id: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    title: Optional[str] = None
    price: Optional[float] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    address: Optional[str] = None
    size_m2: Optional[float] = None
    rooms: Optional[int] = None
    bathrooms: Optional[int] = None
    has_parking: Optional[bool] = None
    has_terrace: Optional[bool] = None
    has_pool: Optional[bool] = None
    has_garden: Optional[bool] = None
    has_trastero: Optional[bool] = None
    garage_spots: Optional[int] = None
    floor: Optional[int] = None
    is_individual: Optional[bool] = None
    is_agency: Optional[bool] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None
    opportunity_score: Optional[int] = None
    opportunity_reasons: Optional[List[str]] = None
    category_id: Optional[int] = None
    catastro_ref: Optional[str] = None
    year_built: Optional[int] = None
    is_active: bool = True
    last_seen_at: Optional[datetime] = None
    content_hash: Optional[str] = None


class PropertyOut(PropertyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class FacebookGroup(BaseModel):
    id: str
    name: str = ""
    enabled: bool = True


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cities: List[str] = Field(default_factory=list)
    max_price: int = 300000
    min_rooms: int = 2
    min_size_m2: int = 60
    portals: str = "Fotocasa, Habitaclia, Pisos.com, Facebook"
    max_leads_per_portal: int = 10
    target_leads: int = 10
    mass_scrape_target: int = 500
    mass_fb_scroll_steps: int = 100
    facebook_groups: List[FacebookGroup] = Field(default_factory=list)
    portal_urls: List[str] = Field(default_factory=list)
    updated_at: Optional[datetime] = None


class SettingsUpdate(BaseModel):
    cities: Optional[List[str]] = None
    max_price: Optional[int] = None
    min_rooms: Optional[int] = None
    min_size_m2: Optional[int] = None
    portals: Optional[str] = None
    max_leads_per_portal: Optional[int] = None
    target_leads: Optional[int] = None
    mass_scrape_target: Optional[int] = None
    mass_fb_scroll_steps: Optional[int] = None
    facebook_groups: Optional[List[FacebookGroup]] = None
    portal_urls: Optional[List[str]] = None


class ScrapingRequestCreate(BaseModel):
    status: str = "pending"
    source_name: Optional[str] = None
    target_leads: Optional[int] = None
    groups: Optional[List[str]] = None
    portal_urls: Optional[List[str]] = None


class ScrapingRequestUpdate(BaseModel):
    status: Optional[str] = None
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ScrapingRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    requested_at: datetime
    processed_at: Optional[datetime] = None
    source_name: Optional[str] = None
    error_message: Optional[str] = None
    target_leads: Optional[int] = None
    groups: Optional[List[str]] = None
    portal_urls: Optional[List[str]] = None


class BatchDeleteRequest(BaseModel):
    ids: List[int]


class BatchCategoryRequest(BaseModel):
    ids: List[int]
    category_id: Optional[int] = None


class SimilarPropertyRequest(BaseModel):
    text: str
    limit: int = 5
    min_similarity: float = 0.75


class SimilarPropertyMatch(BaseModel):
    id: int
    url: str
    title: Optional[str] = None
    price: float = 0
    city: Optional[str] = None
    similarity: float


class PropertyStatsBySource(BaseModel):
    source: str
    active: int
    inactive: int
    total: int


class DatabaseStatsResponse(BaseModel):
    total_active: int
    total_inactive: int
    total: int
    by_source: List[PropertyStatsBySource]
    without_embedding: int
    total_embedded: int = 0
    embedding_available: bool = False
    embedding_model: str = "text-embedding-3-small"
    stale_7d: int
    last_sync: Optional[dict] = None
    sync_in_progress: Optional[dict] = None


class EmbedBackfillResponse(BaseModel):
    embedded: int
    available: bool
    remaining: int = 0
    message: Optional[str] = None


class SyncStartRequest(BaseModel):
    sources: List[str] = Field(default_factory=list)


class SyncStartResponse(BaseModel):
    sync_run_id: int
    status: str


class SyncFinalizeRequest(BaseModel):
    seen_urls: List[str]
    sources: List[str] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)
    deactivate_missing: bool = True


class SyncFinalizeResponse(BaseModel):
    deactivated: int
    created: int = 0
    updated: int = 0
    unchanged: int = 0


class PropertyListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    color: str
    property_ids: List[int] = Field(default_factory=list)
    property_count: int = 0
    created_at: datetime
    updated_at: datetime


class PropertyListCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = None
    color: str = "#6366f1"


class PropertyListUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = None
    color: Optional[str] = None


class ListPropertiesRequest(BaseModel):
    property_ids: List[int] = Field(default_factory=list)


class FindByFieldsRequest(BaseModel):
    price: float
    price_tolerance: float = 0.05
    city: Optional[str] = None
    rooms: Optional[int] = None
    limit: int = 3


class FindByFieldsMatch(BaseModel):
    id: int
    url: str
    title: Optional[str] = None
    price: float = 0
    city: Optional[str] = None
    rooms: Optional[int] = None
