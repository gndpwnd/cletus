"""
app/services/analysis_service.py
Article analysis and prioritization service
"""
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import List, Optional
from collections import Counter
import re

from models.models import Article

class AnalysisService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using word overlap"""
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    async def find_duplicates(self, similarity_threshold: float = 0.8,
                             date_from: Optional[datetime] = None) -> List[dict]:
        """Find duplicate or similar articles"""
        query = select(Article)
        
        if date_from:
            query = query.where(Article.date_scraped >= date_from)
        else:
            # Default to last 24 hours
            query = query.where(
                Article.date_scraped >= datetime.now() - timedelta(hours=24)
            )
        
        result = await self.db.execute(query)
        articles = result.scalars().all()
        
        # Group similar articles
        duplicate_groups = []
        processed = set()
        
        for i, article1 in enumerate(articles):
            if article1.id in processed:
                continue
            
            group = [article1]
            processed.add(article1.id)
            
            for article2 in articles[i+1:]:
                if article2.id in processed:
                    continue
                
                similarity = self._calculate_similarity(
                    article1.headline,
                    article2.headline
                )
                
                if similarity >= similarity_threshold:
                    group.append(article2)
                    processed.add(article2.id)
            
            if len(group) > 1:
                duplicate_groups.append({
                    "count": len(group),
                    "articles": [{
                        "id": a.id,
                        "headline": a.headline,
                        "source": a.source,
                        "link": a.link
                    } for a in group]
                })
        
        return duplicate_groups
    
    async def get_trending_topics(self, hours: int = 24, 
                                  min_articles: int = 3) -> List[dict]:
        """Identify trending topics based on keyword frequency"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        result = await self.db.execute(
            select(Article).where(Article.date_scraped >= cutoff)
        )
        articles = result.scalars().all()
        
        # Extract keywords (simple approach)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 
                     'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was',
                     'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do',
                     'does', 'did', 'will', 'would', 'could', 'should', 'may',
                     'might', 'must', 'can', 'this', 'that', 'these', 'those'}
        
        all_words = []
        for article in articles:
            words = re.findall(r'\b[a-z]{4,}\b', article.headline.lower())
            all_words.extend([w for w in words if w not in stop_words])
        
        # Count word frequency
        word_freq = Counter(all_words)
        
        # Find articles for each trending keyword
        trending = []
        for word, count in word_freq.most_common(20):
            if count >= min_articles:
                related_articles = [
                    a for a in articles 
                    if word in a.headline.lower()
                ]
                
                trending.append({
                    "keyword": word,
                    "article_count": count,
                    "sources": list(set(a.source for a in related_articles)),
                    "sample_headlines": [a.headline for a in related_articles[:3]]
                })
        
        return trending
    
    async def calculate_priority_scores(self, category: Optional[str] = None,
                                       limit: int = 50) -> List[dict]:
        """Calculate priority scores for articles"""
        query = select(Article).where(Article.priority_score.is_(None))
        
        if category:
            query = query.where(Article.category == category)
        
        query = query.order_by(Article.date_scraped.desc()).limit(limit)
        result = await self.db.execute(query)
        articles = result.scalars().all()
        
        prioritized = []
        
        for article in articles:
            score = 0.0
            
            # Factor 1: Headline length (moderate length preferred)
            headline_len = len(article.headline.split())
            if 8 <= headline_len <= 15:
                score += 2.0
            elif 6 <= headline_len <= 20:
                score += 1.0
            
            # Factor 2: Source diversity (check if topic covered by multiple sources)
            result2 = await self.db.execute(
                select(func.count(Article.id))
                .where(
                    Article.headline.ilike(f"%{article.headline.split()[0]}%"),
                    Article.id != article.id
                )
            )
            coverage_count = result2.scalar()
            score += min(coverage_count * 0.5, 3.0)
            
            # Factor 3: Recency (newer = higher score)
            hours_old = (datetime.now() - article.date_scraped).total_seconds() / 3600
            if hours_old < 6:
                score += 3.0
            elif hours_old < 12:
                score += 2.0
            elif hours_old < 24:
                score += 1.0
            
            # Update article with score
            article.priority_score = round(score, 2)
            
            prioritized.append({
                "id": article.id,
                "headline": article.headline,
                "source": article.source,
                "category": article.category,
                "priority_score": article.priority_score,
                "link": article.link
            })
        
        await self.db.commit()
        
        # Sort by priority score
        prioritized.sort(key=lambda x: x["priority_score"], reverse=True)
        
        return prioritized