"""
app/api/scraper.py
Web scraping endpoints
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Dict

from core.database import get_db
from services.scraper_service import ScraperService
from schemas.scraper_schemas import (
    ScrapeRequest, ScrapeResponse, ScrapeStatusResponse
)

router = APIRouter()

@router.post("/scrape", response_model=ScrapeResponse)
async def trigger_scrape(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Trigger a scraping session"""
    scraper = ScraperService(db)
    
    # Generate session ID
    session_id = f"{request.session_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Run scraping in background
    background_tasks.add_task(
        scraper.run_scrape_session,
        session_id=session_id,
        categories=request.categories,
        sources=request.sources
    )
    
    return ScrapeResponse(
        message="Scraping session started",
        session_id=session_id,
        status="started"
    )

@router.get("/status/{session_id}", response_model=ScrapeStatusResponse)
async def get_scrape_status(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get status of a scraping session"""
    from models.models import ScrapeLog
    
    result = await db.execute(
        select(ScrapeLog).where(ScrapeLog.session_id == session_id)
    )
    logs = result.scalars().all()
    
    if not logs:
        return ScrapeStatusResponse(
            session_id=session_id,
            status="not_found",
            total_sources=0,
            completed_sources=0,
            failed_sources=0,
            total_articles=0
        )
    
    completed = sum(1 for log in logs if log.status == "success")
    failed = sum(1 for log in logs if log.status in ["error", "timeout"])
    total_articles = sum(log.articles_found for log in logs)
    
    # Determine overall status
    if completed + failed == len(logs):
        status = "completed"
    else:
        status = "in_progress"
    
    return ScrapeStatusResponse(
        session_id=session_id,
        status=status,
        total_sources=len(logs),
        completed_sources=completed,
        failed_sources=failed,
        total_articles=total_articles,
        logs=[{
            "source": log.source,
            "category": log.category,
            "status": log.status,
            "articles_found": log.articles_found,
            "error": log.error_message
        } for log in logs]
    )

@router.get("/categories")
async def get_available_categories():
    """Get list of available scraping categories"""
    from core.sources import LINK_DICTIONARIES
    
    return {
        "categories": list(LINK_DICTIONARIES.keys()),
        "total": len(LINK_DICTIONARIES)
    }

@router.get("/sources")
async def get_available_sources(category: str = None):
    """Get list of available sources, optionally filtered by category"""
    from app.core.sources import LINK_DICTIONARIES
    
    if category:
        if category not in LINK_DICTIONARIES:
            return {"sources": [], "category": category}
        return {
            "category": category,
            "sources": list(LINK_DICTIONARIES[category].keys())
        }
    
    all_sources = {}
    for cat, sources in LINK_DICTIONARIES.items():
        all_sources[cat] = list(sources.keys())
    
    return {"sources_by_category": all_sources}