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
    is_individual: bool = False
    is_agency: bool = True
    description: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    opportunity_score: int = 0
    opportunity_reasons: List[str] = Field(default_factory=list)
    category_id: Optional[int] = None
    catastro_ref: Optional[str] = None
    year_built: Optional[int] = None


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
    is_individual: Optional[bool] = None
    is_agency: Optional[bool] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None
    opportunity_score: Optional[int] = None
    opportunity_reasons: Optional[List[str]] = None
    category_id: Optional[int] = None
    catastro_ref: Optional[str] = None
    year_built: Optional[int] = None


class PropertyOut(PropertyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


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
    facebook_groups: List[str] = Field(default_factory=list)
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
    facebook_groups: Optional[List[str]] = None
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


class EmbedBackfillResponse(BaseModel):
    embedded: int
    available: bool
