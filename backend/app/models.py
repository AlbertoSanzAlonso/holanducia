from datetime import datetime
from typing import Optional, List, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#00acee")


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(64))
    url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(100))
    title: Mapped[Optional[str]] = mapped_column(String(500))
    price: Mapped[float] = mapped_column(Float, default=0)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    neighborhood: Mapped[Optional[str]] = mapped_column(String(100))
    address: Mapped[Optional[str]] = mapped_column(String(300))
    size_m2: Mapped[Optional[float]] = mapped_column(Float)
    rooms: Mapped[Optional[int]] = mapped_column(Integer)
    bathrooms: Mapped[Optional[int]] = mapped_column(Integer)
    has_parking: Mapped[bool] = mapped_column(Boolean, default=False)
    has_terrace: Mapped[bool] = mapped_column(Boolean, default=False)
    has_pool: Mapped[bool] = mapped_column(Boolean, default=False)
    is_individual: Mapped[bool] = mapped_column(Boolean, default=False)
    is_agency: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    images: Mapped[list] = mapped_column(JSONB, default=list)
    opportunity_score: Mapped[int] = mapped_column(Integer, default=0)
    opportunity_reasons: Mapped[list] = mapped_column(JSONB, default=list)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"))
    catastro_ref: Mapped[Optional[str]] = mapped_column(String(100))
    year_built: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), default="running")
    sources: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    stats: Mapped[dict] = mapped_column(JSONB, default=dict)


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    cities: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    max_price: Mapped[int] = mapped_column(Integer, default=300000)
    min_rooms: Mapped[int] = mapped_column(Integer, default=2)
    min_size_m2: Mapped[int] = mapped_column(Integer, default=60)
    portals: Mapped[str] = mapped_column(String(200), default="Fotocasa, Habitaclia, Pisos.com, Facebook")
    max_leads_per_portal: Mapped[int] = mapped_column(Integer, default=10)
    target_leads: Mapped[int] = mapped_column(Integer, default=10)
    mass_scrape_target: Mapped[int] = mapped_column(Integer, default=500)
    mass_fb_scroll_steps: Mapped[int] = mapped_column(Integer, default=100)
    facebook_groups: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    portal_urls: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScrapingRequest(Base):
    __tablename__ = "scraping_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    source_name: Mapped[Optional[str]] = mapped_column(String(100))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    target_leads: Mapped[Optional[int]] = mapped_column(Integer)
    groups: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    portal_urls: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
