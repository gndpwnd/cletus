"""
app/api/articles.py
Articles management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta

from core.database import get_db
from models.models import Article
from schemas.article_schemas import (
    ArticleCreate, ArticleResponse, ArticleUpdate,
    ArticleListResponse, ArticleStats
)

router = APIRouter()

@router.get("/", response_model=ArticleListResponse)
async def get_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    category: Optional[str] = None,
    source: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    is_selected: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get articles with filtering and pagination"""
    query = select(Article)
    
    # Apply filters
    filters = []
    if category:
        filters.append(Article.category == category)
    if source:
        filters.append(Article.source == source)
    if date_from:
        filters.append(Article.date_scraped >= date_from)
    if date_to:
        filters.append(Article.date_scraped <= date_to)
    if is_selected is not None:
        filters.append(Article.is_selected == is_selected)
    if search:
        search_filter = or_(
            Article.headline.ilike(f"%{search}%"),
            Article.source.ilike(f"%{search}%")
        )
        filters.append(search_filter)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    count_query = select(func.count()).select_from(Article).where(and_(*filters) if filters else True)
    result = await db.execute(count_query)
    total = result.scalar()
    
    # Apply pagination and ordering
    query = query.order_by(Article.date_scraped.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    articles = result.scalars().all()
    
    return ArticleListResponse(
        articles=[ArticleResponse.from_orm(a) for a in articles],
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/stats", response_model=ArticleStats)
async def get_article_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get statistics about articles"""
    # Total articles
    total_result = await db.execute(select(func.count()).select_from(Article))
    total = total_result.scalar()
    
    # Articles today
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.count()).select_from(Article).where(Article.date_scraped >= today_start)
    )
    today = today_result.scalar()
    
    # Selected articles
    selected_result = await db.execute(
        select(func.count()).select_from(Article).where(Article.is_selected == True)
    )
    selected = selected_result.scalar()
    
    # By category
    category_result = await db.execute(
        select(Article.category, func.count(Article.id))
        .group_by(Article.category)
    )
    by_category = {cat: count for cat, count in category_result.all()}
    
    # By source
    source_result = await db.execute(
        select(Article.source, func.count(Article.id))
        .group_by(Article.source)
        .order_by(func.count(Article.id).desc())
        .limit(10)
    )
    by_source = {src: count for src, count in source_result.all()}
    
    return ArticleStats(
        total_articles=total,
        articles_today=today,
        selected_articles=selected,
        by_category=by_category,
        top_sources=by_source
    )

@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific article by ID"""
    result = await db.execute(
        select(Article).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return ArticleResponse.from_orm(article)

@router.patch("/{article_id}", response_model=ArticleResponse)
async def update_article(
    article_id: int,
    article_update: ArticleUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an article"""
    result = await db.execute(
        select(Article).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Update fields
    update_data = article_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(article, field, value)
    
    await db.commit()
    await db.refresh(article)
    
    return ArticleResponse.from_orm(article)

@router.delete("/{article_id}")
async def delete_article(
    article_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete an article"""
    result = await db.execute(
        select(Article).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    await db.delete(article)
    await db.commit()
    
    return {"message": "Article deleted successfully"}

@router.post("/bulk-select")
async def bulk_select_articles(
    article_ids: List[int],
    selected: bool,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update article selection status"""
    result = await db.execute(
        select(Article).where(Article.id.in_(article_ids))
    )
    articles = result.scalars().all()
    
    for article in articles:
        article.is_selected = selected
    
    await db.commit()
    
    return {"message": f"Updated {len(articles)} articles", "count": len(articles)}

@router.delete("/cleanup")
async def cleanup_old_articles(
    days: int = Query(10, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Delete articles older than specified days"""
    cutoff_date = datetime.now() - timedelta(days=days)
    
    result = await db.execute(
        select(Article).where(Article.date_scraped < cutoff_date)
    )
    articles = result.scalars().all()
    
    count = len(articles)
    for article in articles:
        await db.delete(article)
    
    await db.commit()
    
    return {"message": f"Deleted {count} articles older than {days} days", "count": count}