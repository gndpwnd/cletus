"""
app/api/scraper.py
Web scraping endpoints with comprehensive session tracking and 5-minute cooldown protection
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from core.database import get_db
from services.scraper_service import ScraperService
from schemas.scraper_schemas import (
    ScrapeRequest, ScrapeResponse, ScrapeStatusResponse
)
from models.models import ScrapeLog, ScrapeSession
from core.config import settings

router = APIRouter()

# Cooldown settings
SCRAPE_COOLDOWN_MINUTES = settings.SCRAPE_COOLDOWN_MINUTES

async def check_scrape_cooldown(db: AsyncSession) -> tuple[bool, datetime | None]:
    """
    Check if scraping is on cooldown.
    Returns (is_on_cooldown, last_scrape_time)
    """
    # Get the most recent scrape session start time
    result = await db.execute(
        select(ScrapeSession.start_time)
        .order_by(desc(ScrapeSession.start_time))
        .limit(1)
    )
    last_scrape = result.scalar_one_or_none()
    
    if not last_scrape:
        return False, None
    
    # Ensure we're working with timezone-aware datetimes
    now = datetime.now(timezone.utc)
    if last_scrape.tzinfo is None:
        last_scrape = last_scrape.replace(tzinfo=timezone.utc)
    
    # Check if within cooldown period
    cooldown_end = last_scrape + timedelta(minutes=SCRAPE_COOLDOWN_MINUTES)
    is_on_cooldown = now < cooldown_end
    
    return is_on_cooldown, last_scrape

@router.post("/scrape", response_model=ScrapeResponse)
async def trigger_scrape(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Trigger a scraping session with cooldown protection"""
    
    # Check cooldown
    is_on_cooldown, last_scrape = await check_scrape_cooldown(db)
    
    if is_on_cooldown:
        now = datetime.now(timezone.utc)
        if last_scrape.tzinfo is None:
            last_scrape = last_scrape.replace(tzinfo=timezone.utc)
        
        cooldown_end = last_scrape + timedelta(minutes=SCRAPE_COOLDOWN_MINUTES)
        remaining_seconds = int((cooldown_end - now).total_seconds())
        remaining_minutes = remaining_seconds // 60
        remaining_secs = remaining_seconds % 60
        
        raise HTTPException(
            status_code=429,
            detail={
                "message": f"Scraping is on cooldown. Please wait {remaining_minutes}m {remaining_secs}s",
                "cooldown_end": cooldown_end.isoformat(),
                "remaining_seconds": remaining_seconds,
                "last_scrape": last_scrape.isoformat()
            }
        )
    
    scraper = ScraperService(db)
    
    # Generate session ID
    session_id = f"{request.session_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Run scraping in background
    background_tasks.add_task(
        scraper.run_scrape_session,
        session_id=session_id,
        session_type=request.session_type,
        categories=request.categories,
        sources=request.sources
    )
    
    return ScrapeResponse(
        message="Scraping session started",
        session_id=session_id,
        status="started"
    )

@router.get("/cooldown-status")
async def get_cooldown_status(db: AsyncSession = Depends(get_db)):
    """Check current cooldown status"""
    is_on_cooldown, last_scrape = await check_scrape_cooldown(db)
    
    if not last_scrape:
        return {
            "on_cooldown": False,
            "can_scrape": True,
            "message": "No recent scrapes. Ready to scrape.",
            "remaining_seconds": 0
        }
    
    now = datetime.now(timezone.utc)
    if last_scrape.tzinfo is None:
        last_scrape = last_scrape.replace(tzinfo=timezone.utc)
    
    if is_on_cooldown:
        cooldown_end = last_scrape + timedelta(minutes=SCRAPE_COOLDOWN_MINUTES)
        remaining_seconds = int((cooldown_end - now).total_seconds())
        remaining_minutes = remaining_seconds // 60
        remaining_secs = remaining_seconds % 60
        
        return {
            "on_cooldown": True,
            "can_scrape": False,
            "last_scrape": last_scrape.isoformat(),
            "cooldown_end": cooldown_end.isoformat(),
            "remaining_seconds": remaining_seconds,
            "message": f"Cooldown active. Wait {remaining_minutes}m {remaining_secs}s"
        }
    
    return {
        "on_cooldown": False,
        "can_scrape": True,
        "last_scrape": last_scrape.isoformat(),
        "remaining_seconds": 0,
        "message": "Ready to scrape"
    }

@router.get("/status/{session_id}")
async def get_scrape_status(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed status of a scraping session with real-time progress"""
    # First try to get the session record
    session_result = await db.execute(
        select(ScrapeSession).where(ScrapeSession.session_id == session_id)
    )
    session = session_result.scalar_one_or_none()
    
    if not session:
        # Fallback to checking logs if session not found
        logs_result = await db.execute(
            select(ScrapeLog).where(ScrapeLog.session_id == session_id)
        )
        logs = logs_result.scalars().all()
        
        if not logs:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Build response from logs only
        completed = sum(1 for log in logs if log.status == "success")
        failed = sum(1 for log in logs if log.status in ["error", "timeout"])
        total_articles = sum(log.articles_found or 0 for log in logs)
        
        return {
            "session_id": session_id,
            "status": "in_progress" if completed + failed < len(logs) else "completed",
            "total_sources": len(logs),
            "completed_sources": completed,
            "failed_sources": failed,
            "total_articles": total_articles,
            "progress_percent": int((completed + failed) / len(logs) * 100) if len(logs) > 0 else 0
        }
    
    # Calculate progress percentage
    progress_percent = 0
    if session.total_sources > 0:
        progress_percent = int((session.completed_sources + session.failed_sources) / session.total_sources * 100)
    
    # Return comprehensive session data
    return {
        "session_id": session.session_id,
        "session_type": session.session_type,
        "status": session.status,
        "start_time": session.start_time.isoformat() if session.start_time else None,
        "end_time": session.end_time.isoformat() if session.end_time else None,
        "categories": session.get_categories(),
        "total_sources": session.total_sources,
        "completed_sources": session.completed_sources,
        "failed_sources": session.failed_sources,
        "total_articles": session.total_articles_found,
        "new_articles": session.new_articles,
        "updated_articles": session.updated_articles,
        "duration_seconds": session.duration_seconds,
        "progress_percent": progress_percent,
        "error_message": session.error_message
    }

@router.get("/sessions")
async def get_scrape_sessions(
    limit: int = 10,
    skip: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get list of scraping sessions with comprehensive stats"""
    # Query ScrapeSession table for complete session data
    result = await db.execute(
        select(ScrapeSession)
        .order_by(desc(ScrapeSession.start_time))
        .offset(skip)
        .limit(limit)
    )
    sessions = result.scalars().all()
    
    sessions_data = []
    for session in sessions:
        # Calculate progress for in-progress sessions
        progress_percent = 0
        if session.total_sources > 0:
            progress_percent = int((session.completed_sources + session.failed_sources) / session.total_sources * 100)
        
        sessions_data.append({
            "session_id": session.session_id,
            "session_type": session.session_type,
            "start_time": session.start_time.isoformat() if session.start_time else None,
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "status": session.status,
            "categories": session.get_categories(),
            "total_sources": session.total_sources,
            "completed_sources": session.completed_sources,
            "failed_sources": session.failed_sources,
            "articles_found": session.total_articles_found,
            "new_articles": session.new_articles,
            "updated_articles": session.updated_articles,
            "duration_seconds": session.duration_seconds,
            "progress_percent": progress_percent,
            "error_message": session.error_message if session.status == "error" else None
        })
    
    return sessions_data

@router.get("/sessions/{session_id}/logs")
async def get_session_logs(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed logs for a specific session (individual source results)"""
    # Verify session exists
    session_result = await db.execute(
        select(ScrapeSession).where(ScrapeSession.session_id == session_id)
    )
    session = session_result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get all logs for this session
    logs_result = await db.execute(
        select(ScrapeLog)
        .where(ScrapeLog.session_id == session_id)
        .order_by(ScrapeLog.scrape_time)
    )
    logs = logs_result.scalars().all()
    
    logs_data = []
    for log in logs:
        logs_data.append({
            "source": log.source,
            "category": log.category,
            "status": log.status,
            "articles_found": log.articles_found or 0,
            "articles_updated": log.articles_updated or 0,
            "scrape_time": log.scrape_time.isoformat() if log.scrape_time else None,
            "duration_seconds": log.duration_seconds,
            "error_message": log.error_message
        })
    
    return {
        "session_id": session_id,
        "total_logs": len(logs_data),
        "logs": logs_data
    }

@router.get("/sessions/stats/summary")
async def get_sessions_summary(
    days: int = 7,
    db: AsyncSession = Depends(get_db)
):
    """Get summary statistics for scraping sessions over time"""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    result = await db.execute(
        select(ScrapeSession)
        .where(ScrapeSession.start_time >= cutoff_date)
        .order_by(desc(ScrapeSession.start_time))
    )
    sessions = result.scalars().all()
    
    # Calculate aggregate stats
    total_sessions = len(sessions)
    successful_sessions = sum(1 for s in sessions if s.status == "completed")
    failed_sessions = sum(1 for s in sessions if s.status == "error")
    total_articles = sum(s.total_articles_found or 0 for s in sessions)
    total_new_articles = sum(s.new_articles or 0 for s in sessions)
    total_updated_articles = sum(s.updated_articles or 0 for s in sessions)
    
    # Category breakdown
    category_stats = {}
    for session in sessions:
        for category in session.get_categories():
            if category not in category_stats:
                category_stats[category] = {
                    "scrape_count": 0,
                    "total_sources": 0,
                    "completed_sources": 0,
                    "failed_sources": 0
                }
            category_stats[category]["scrape_count"] += 1
    
    # Get per-category source counts
    for category in category_stats.keys():
        logs_result = await db.execute(
            select(ScrapeLog)
            .where(ScrapeLog.category == category)
            .where(ScrapeLog.scrape_time >= cutoff_date)
        )
        logs = logs_result.scalars().all()
        
        category_stats[category]["total_sources"] = len(logs)
        category_stats[category]["completed_sources"] = sum(1 for log in logs if log.status == "success")
        category_stats[category]["failed_sources"] = sum(1 for log in logs if log.status in ["error", "timeout"])
    
    # Session type breakdown
    session_type_stats = {}
    for session in sessions:
        session_type = session.session_type
        if session_type not in session_type_stats:
            session_type_stats[session_type] = {
                "count": 0,
                "articles_found": 0,
                "avg_duration": 0
            }
        session_type_stats[session_type]["count"] += 1
        session_type_stats[session_type]["articles_found"] += session.total_articles_found or 0
    
    # Calculate average durations
    for session_type in session_type_stats:
        type_sessions = [s for s in sessions if s.session_type == session_type and s.duration_seconds]
        if type_sessions:
            avg_duration = sum(s.duration_seconds for s in type_sessions) / len(type_sessions)
            session_type_stats[session_type]["avg_duration"] = round(avg_duration, 2)
    
    return {
        "period_days": days,
        "total_sessions": total_sessions,
        "successful_sessions": successful_sessions,
        "failed_sessions": failed_sessions,
        "in_progress_sessions": total_sessions - successful_sessions - failed_sessions,
        "total_articles_found": total_articles,
        "total_new_articles": total_new_articles,
        "total_updated_articles": total_updated_articles,
        "category_breakdown": category_stats,
        "session_type_breakdown": session_type_stats,
        "recent_sessions": [
            {
                "session_id": s.session_id,
                "session_type": s.session_type,
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "status": s.status,
                "articles_found": s.total_articles_found
            }
            for s in sessions[:5]  # Last 5 sessions
        ]
    }

@router.get("/categories")
async def get_available_categories():
    """Get list of available scraping categories"""
    from core.sources import LINK_DICTIONARIES
    
    categories_info = []
    for category, sources in LINK_DICTIONARIES.items():
        categories_info.append({
            "name": category,
            "source_count": len(sources),
            "sources": list(sources.keys())
        })
    
    return {
        "categories": [c["name"] for c in categories_info],
        "total_categories": len(LINK_DICTIONARIES),
        "detailed_info": categories_info
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
            "sources": list(LINK_DICTIONARIES[category].keys()),
            "total_sources": len(LINK_DICTIONARIES[category])
        }
    
    all_sources = {}
    total_sources = 0
    for cat, sources in LINK_DICTIONARIES.items():
        all_sources[cat] = list(sources.keys())
        total_sources += len(sources)
    
    return {
        "sources_by_category": all_sources,
        "total_sources": total_sources,
        "total_categories": len(LINK_DICTIONARIES)
    }