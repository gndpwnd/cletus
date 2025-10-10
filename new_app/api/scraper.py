"""
app/api/scraper.py
Web scraping endpoints - COMPLETE VERSION WITH /sessions ENDPOINT
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
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

@router.get("/sessions")
async def get_scrape_sessions(
    limit: int = 10,
    skip: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get list of scraping sessions with their stats"""
    from models.models import ScrapeLog
    
    # Get distinct session IDs ordered by most recent
    session_query = (
        select(ScrapeLog.session_id, func.min(ScrapeLog.start_time).label('start_time'))
        .group_by(ScrapeLog.session_id)
        .order_by(func.min(ScrapeLog.start_time).desc())
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(session_query)
    sessions_data = result.all()
    
    sessions = []
    for session_id, start_time in sessions_data:
        # Get logs for this session
        logs_result = await db.execute(
            select(ScrapeLog).where(ScrapeLog.session_id == session_id)
        )
        logs = logs_result.scalars().all()
        
        # Calculate stats
        completed = sum(1 for log in logs if log.status == "success")
        failed = sum(1 for log in logs if log.status in ["error", "timeout"])
        total_sources = len(logs)
        articles_found = sum(log.articles_found or 0 for log in logs)
        
        # Determine overall status
        if completed + failed == total_sources:
            status = "completed"
        elif failed > completed:
            status = "error"
        else:
            status = "in_progress"
        
        # Calculate duration
        duration_seconds = None
        if logs:
            durations = [log.duration_seconds for log in logs if log.duration_seconds]
            if durations:
                duration_seconds = sum(durations)
        
        sessions.append({
            "session_id": session_id,
            "start_time": start_time.isoformat() if start_time else None,
            "status": status,
            "total_sources": total_sources,
            "completed_sources": completed,
            "failed_sources": failed,
            "articles_found": articles_found,
            "duration_seconds": duration_seconds
        })
    
    return sessions

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
    from core.sources import LINK_DICTIONARIES
    
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