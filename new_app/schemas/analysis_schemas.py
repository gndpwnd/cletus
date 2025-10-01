"""Analysis schemas"""
from pydantic import BaseModel
from typing import List

class DuplicateGroup(BaseModel):
    count: int
    articles: List[dict]

class TrendingTopic(BaseModel):
    keyword: str
    article_count: int
    sources: List[str]
    sample_headlines: List[str]

class ArticlePriority(BaseModel):
    id: int
    headline: str
    source: str
    category: str
    priority_score: float
    link: str