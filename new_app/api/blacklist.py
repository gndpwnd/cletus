"""
app/api/blacklist.py
Blacklist management endpoints with dual persistence
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from core.database import get_db
from services.blacklist_service import BlacklistService
from schemas.blacklist_schemas import (
    BlacklistCreate, BlacklistResponse, BlacklistUpdate
)

router = APIRouter()

@router.get("/", response_model=List[BlacklistResponse])
async def get_blacklist(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Get blacklisted URL patterns"""
    from sqlalchemy import select
    from app.models.models import Blacklist
    
    query = select(Blacklist)
    
    if active_only:
        query = query.where(Blacklist.is_active == True)
    
    query = query.order_by(Blacklist.date_added.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    blacklist_entries = result.scalars().all()
    
    return [BlacklistResponse.model_validate(entry) for entry in blacklist_entries]

@router.post("/", response_model=BlacklistResponse)
async def add_to_blacklist(
    blacklist: BlacklistCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add a URL pattern to blacklist (saves to both DB and JSON)"""
    service = BlacklistService(db)
    
    entry = await service.add_pattern(
        pattern=blacklist.url_pattern,
        reason=blacklist.reason
    )
    
    return BlacklistResponse.model_validate(entry)

@router.patch("/{blacklist_id}", response_model=BlacklistResponse)
async def update_blacklist(
    blacklist_id: int,
    blacklist_update: BlacklistUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a blacklist entry"""
    from sqlalchemy import select
    from app.models.models import Blacklist
    
    result = await db.execute(
        select(Blacklist).where(Blacklist.id == blacklist_id)
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Blacklist entry not found")
    
    update_data = blacklist_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entry, field, value)
    
    await db.commit()
    await db.refresh(entry)
    
    # Sync to JSON
    service = BlacklistService(db)
    await service.sync_from_db_to_json()
    
    return BlacklistResponse.model_validate(entry)

@router.delete("/{blacklist_id}")
async def delete_blacklist(
    blacklist_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete (deactivate) a blacklist entry"""
    from sqlalchemy import select
    from app.models.models import Blacklist
    
    result = await db.execute(
        select(Blacklist).where(Blacklist.id == blacklist_id)
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Blacklist entry not found")
    
    service = BlacklistService(db)
    await service.remove_pattern(entry.url_pattern)
    
    return {"message": "Blacklist entry deactivated"}

@router.post("/check")
async def check_blacklist(
    url: str,
    db: AsyncSession = Depends(get_db)
):
    """Check if a URL is blacklisted"""
    service = BlacklistService(db)
    patterns = await service.get_all_active()
    
    for pattern in patterns:
        if url.startswith(pattern):
            return {
                "is_blacklisted": True,
                "matched_pattern": pattern
            }
    
    return {"is_blacklisted": False}

@router.post("/bulk-add")
async def bulk_add_to_blacklist(
    patterns: List[str],
    reason: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Bulk add URL patterns to blacklist"""
    service = BlacklistService(db)
    added = 0
    skipped = 0
    
    for pattern in patterns:
        try:
            await service.add_pattern(pattern, reason)
            added += 1
        except:
            skipped += 1
    
    return {
        "message": f"Added {added} patterns, skipped {skipped}",
        "added": added,
        "skipped": skipped
    }

@router.post("/sync-json-to-db")
async def sync_json_to_db(db: AsyncSession = Depends(get_db)):
    """Manually sync JSON blacklist to database"""
    service = BlacklistService(db)
    await service.sync_from_json_to_db()
    return {"message": "Blacklist synced from JSON to database"}

@router.post("/sync-db-to-json")
async def sync_db_to_json(db: AsyncSession = Depends(get_db)):
    """Manually sync database blacklist to JSON"""
    service = BlacklistService(db)
    await service.sync_from_db_to_json()
    return {"message": "Blacklist synced from database to JSON"}