from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models import Category, Property, ScrapingRequest, UserSettings
from backend.app.schemas import (
    BatchCategoryRequest,
    BatchDeleteRequest,
    CategoryOut,
    EmbedBackfillResponse,
    PropertyCreate,
    PropertyOut,
    PropertyUpdate,
    ScrapingRequestCreate,
    ScrapingRequestOut,
    ScrapingRequestUpdate,
    SettingsOut,
    SettingsUpdate,
    SimilarPropertyMatch,
    SimilarPropertyRequest,
    SyncFinalizeRequest,
    SyncFinalizeResponse,
    SyncStartRequest,
    SyncStartResponse,
)
from backend.app.services.vector_service import VectorService
from backend.app.services.opportunity_service import OpportunityService
from backend.app.services.sync_service import SyncService, compute_content_hash

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "/app/media/properties"))

PROPERTY_FIELDS = {
    "external_id", "url", "source", "title", "price", "city", "neighborhood", "address",
    "size_m2", "rooms", "bathrooms", "has_parking", "has_terrace", "has_pool",
    "is_individual", "is_agency", "description", "images", "opportunity_score",
    "opportunity_reasons", "category_id", "catastro_ref", "year_built",
    "is_active", "last_seen_at", "content_hash",
}


def apply_opportunity_score(data: dict) -> dict:
    analysis = OpportunityService.calculate_score(
        current_price=float(data.get("price") or 0),
        previous_price=None,
        market_avg_price=3200.0,
        is_individual=bool(data.get("is_individual")),
    )
    data["opportunity_score"] = analysis["score"]
    data["opportunity_reasons"] = analysis["reasons"]
    return data


def property_to_dict(prop: Property) -> dict:
    return {field: getattr(prop, field) for field in PROPERTY_FIELDS | {"id", "created_at", "updated_at"}}


@router.get("/media/properties/{filename}")
async def serve_property_image(filename: str):
    safe = Path(filename).name
    path = MEDIA_ROOT / safe
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)


@router.get("/categories", response_model=List[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.name))
    return result.scalars().all()


@router.get("/properties", response_model=List[PropertyOut])
async def list_properties(active_only: bool = True, db: AsyncSession = Depends(get_db)):
    query = select(Property).order_by(Property.created_at.desc())
    if active_only:
        query = query.where(Property.is_active.is_(True))
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/properties/by-url", response_model=Optional[PropertyOut])
async def get_property_by_url(url: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Property).where(Property.url == url))
    return result.scalar_one_or_none()


@router.post("/properties", response_model=PropertyOut)
async def upsert_property(payload: PropertyCreate, db: AsyncSession = Depends(get_db)):
    data = apply_opportunity_score(payload.model_dump())
    data["content_hash"] = compute_content_hash(data)
    data["is_active"] = True
    data["last_seen_at"] = datetime.now(timezone.utc)
    result = await db.execute(select(Property).where(Property.url == data["url"]))
    existing = result.scalar_one_or_none()

    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing)
        try:
            await VectorService(db).upsert_property_embedding(existing)
        except Exception as e:
            logger.warning("Embedding falló al actualizar property #%s: %s", existing.id, e)
        return existing

    prop = Property(**data)
    db.add(prop)
    await db.commit()
    await db.refresh(prop)

    try:
        await VectorService(db).upsert_property_embedding(prop)
    except Exception as e:
        logger.warning("Embedding falló al crear property #%s: %s", prop.id, e)

    return prop


@router.patch("/properties/{property_id}", response_model=PropertyOut)
async def update_property(property_id: int, payload: PropertyUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Property).where(Property.id == property_id))
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(prop, key, value)

    if "price" in updates or "is_individual" in updates:
        analysis = OpportunityService.calculate_score(
            current_price=float(prop.price or 0),
            previous_price=None,
            market_avg_price=3200.0,
            is_individual=bool(prop.is_individual),
        )
        prop.opportunity_score = analysis["score"]
        prop.opportunity_reasons = analysis["reasons"]

    prop.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(prop)
    return prop


@router.delete("/properties/{property_id}", status_code=204)
async def delete_property(property_id: int, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Property).where(Property.id == property_id))
    await db.commit()


@router.post("/properties/batch-delete", status_code=204)
async def batch_delete_properties(payload: BatchDeleteRequest, db: AsyncSession = Depends(get_db)):
    if not payload.ids:
        return
    await db.execute(delete(Property).where(Property.id.in_(payload.ids)))
    await db.commit()


@router.post("/properties/batch-category", status_code=204)
async def batch_update_category(payload: BatchCategoryRequest, db: AsyncSession = Depends(get_db)):
    if not payload.ids:
        return
    await db.execute(
        update(Property)
        .where(Property.id.in_(payload.ids))
        .values(category_id=payload.category_id, updated_at=datetime.now(timezone.utc))
    )
    await db.commit()


@router.post("/properties/similar", response_model=List[SimilarPropertyMatch])
async def find_similar_properties(payload: SimilarPropertyRequest, db: AsyncSession = Depends(get_db)):
    service = VectorService(db)
    if not service.embedder.available:
        return []
    return await service.find_similar(
        payload.text,
        limit=payload.limit,
        min_similarity=payload.min_similarity,
    )


@router.post("/properties/{property_id}/embed", response_model=PropertyOut)
async def embed_property(property_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Property).where(Property.id == property_id))
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    service = VectorService(db)
    if not service.embedder.available:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured for embeddings")

    if not await service.upsert_property_embedding(prop):
        raise HTTPException(status_code=500, detail="Failed to generate embedding")

    await db.refresh(prop)
    return prop


@router.post("/properties/embed-backfill", response_model=EmbedBackfillResponse)
async def embed_backfill(limit: int = 100, db: AsyncSession = Depends(get_db)):
    service = VectorService(db)
    if not service.embedder.available:
        return EmbedBackfillResponse(embedded=0, available=False)
    embedded = await service.backfill_missing(limit=min(limit, 500))
    return EmbedBackfillResponse(embedded=embedded, available=True)


@router.post("/sync/start", response_model=SyncStartResponse)
async def sync_start(payload: SyncStartRequest, db: AsyncSession = Depends(get_db)):
    run = await SyncService(db).start_run(payload.sources)
    return SyncStartResponse(sync_run_id=run.id, status=run.status)


@router.post("/sync/{sync_run_id}/finalize", response_model=SyncFinalizeResponse)
async def sync_finalize(
    sync_run_id: int,
    payload: SyncFinalizeRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await SyncService(db).finalize_run(
        sync_run_id,
        seen_urls=set(payload.seen_urls),
        sources=payload.sources,
        stats=payload.stats,
    )
    return SyncFinalizeResponse(
        deactivated=result.get("deactivated", 0),
        created=result.get("created", 0),
        updated=result.get("updated", 0),
        unchanged=result.get("unchanged", 0),
    )


@router.get("/settings", response_model=SettingsOut)
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserSettings).where(UserSettings.id == 1))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = UserSettings(id=1)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


@router.put("/settings", response_model=SettingsOut)
async def update_settings(payload: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserSettings).where(UserSettings.id == 1))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = UserSettings(id=1)
        db.add(settings)

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)
    settings.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(settings)
    return settings


@router.get("/scraping-requests/latest", response_model=Optional[ScrapingRequestOut])
async def latest_scraping_request(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScrapingRequest).order_by(ScrapingRequest.requested_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/scraping-requests/pending", response_model=Optional[ScrapingRequestOut])
async def pending_scraping_request(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScrapingRequest)
        .where(ScrapingRequest.status == "pending")
        .order_by(ScrapingRequest.requested_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.post("/scraping-requests", response_model=ScrapingRequestOut)
async def create_scraping_request(payload: ScrapingRequestCreate, db: AsyncSession = Depends(get_db)):
    req = ScrapingRequest(**payload.model_dump())
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


@router.patch("/scraping-requests/{request_id}", response_model=ScrapingRequestOut)
async def update_scraping_request(
    request_id: int,
    payload: ScrapingRequestUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ScrapingRequest).where(ScrapingRequest.id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Scraping request not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(req, key, value)

    await db.commit()
    await db.refresh(req)
    return req
