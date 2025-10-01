# ===== api/analysis.py =====
"""
api/analysis.py
Article analysis endpoints
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from datetime import datetime, timedelta

from core.database import get_db
from models.models import Article
from services.analysis_service import AnalysisService
from schemas.analysis_schemas import (
    DuplicateGroup, TrendingTopic, ArticlePriority
)

router = APIRouter()

@router.post("/detect-duplicates")
async def detect_duplicates(
    similarity_threshold: float = Query(0.8, ge=0.5, le=1.0),
    date_from: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """Detect duplicate or similar articles"""
    analyzer = AnalysisService(db)
    duplicates = await analyzer.find_duplicates(
        similarity_threshold=similarity_threshold,
        date_from=date_from
    )
    
    return {
        "duplicate_groups": duplicates,
        "total_groups": len(duplicates)
    }

@router.get("/trending")
async def get_trending_topics(
    hours: int = Query(24, ge=1, le=168),
    min_articles: int = Query(3, ge=2, le=20),
    db: AsyncSession = Depends(get_db)
):
    """Get trending topics based on article frequency"""
    analyzer = AnalysisService(db)
    trending = await analyzer.get_trending_topics(
        hours=hours,
        min_articles=min_articles
    )
    
    return {
        "trending_topics": trending,
        "time_window_hours": hours
    }

@router.post("/prioritize")
async def prioritize_articles(
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Calculate priority scores for articles"""
    analyzer = AnalysisService(db)
    prioritized = await analyzer.calculate_priority_scores(
        category=category,
        limit=limit
    )
    
    return {
        "prioritized_articles": prioritized,
        "total": len(prioritized)
    }

@router.get("/sources/reliability")
async def get_source_reliability(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """Get reliability metrics for news sources"""
    cutoff = datetime.now() - timedelta(days=days)
    
    result = await db.execute(
        select(
            Article.source,
            func.count(Article.id).label('total_articles'),
            func.avg(Article.priority_score).label('avg_priority'),
            func.count(Article.id).filter(Article.is_selected == True).label('selected_count')
        )
        .where(Article.date_scraped >= cutoff)
        .group_by(Article.source)
        .order_by(func.count(Article.id).desc())
    )
    
    sources = []
    for row in result.all():
        selection_rate = (row.selected_count / row.total_articles * 100) if row.total_articles > 0 else 0
        sources.append({
            "source": row.source,
            "total_articles": row.total_articles,
            "avg_priority": round(row.avg_priority, 2) if row.avg_priority else None,
            "selected_count": row.selected_count,
            "selection_rate": round(selection_rate, 2)
        })
    
    return {
        "sources": sources,
        "days_analyzed": days
    }