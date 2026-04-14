from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

class PropertyBase(BaseModel):
    external_id: str
    source: str
    url: str
    title: Optional[str] = None
    price: float
    currency: str = "EUR"
    location_raw: Optional[str] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    rooms: Optional[int] = None
    bathrooms: Optional[int] = None
    size_m2: Optional[float] = None
    description: Optional[str] = None
    images: List[str] = []
    is_individual: bool = False
    is_agency: bool = False
    last_seen: datetime = Field(default_factory=datetime.utcnow)

class PropertyCreate(PropertyBase):
    pass

class PropertyUpdate(BaseModel):
    price: Optional[float] = None
    last_seen: datetime = Field(default_factory=datetime.utcnow)

class PropertyInDB(PropertyBase):
    id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    price_history: List[Dict] = []
    opportunity_score: float = 0.0

    class Config:
        from_attributes = True
