"""Article schemas"""
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict

class ArticleBase(BaseModel):
    headline: str
    link: str
    source: str
    category: str

class ArticleCreate(ArticleBase):
    date_published: Optional[datetime] = None
    scrape_session: Optional[str] = None

class ArticleUpdate(BaseModel):
    is_selected: Optional[bool] = None
    priority_score: Optional[float] = None
    analysis_notes: Optional[str] = None
    is_duplicate: Optional[bool] = None

class ArticleResponse(ArticleBase):
    id: int
    date_scraped: datetime
    date_published: Optional[datetime]
    is_duplicate: bool
    is_selected: bool
    priority_score: Optional[float]
    analysis_notes: Optional[str]
    scrape_session: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)

class ArticleListResponse(BaseModel):
    articles: List[ArticleResponse]
    total: int
    skip: int
    limit: int

class ArticleStats(BaseModel):
    total_articles: int
    articles_today: int
    selected_articles: int
    by_category: Dict[str, int]
    top_sources: Dict[str, int]


# ===== app/schemas/blacklist_schemas.py =====
"""Blacklist schemas"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class BlacklistBase(BaseModel):
    url_pattern: str
    reason: Optional[str] = None

class BlacklistCreate(BlacklistBase):
    pass

class BlacklistUpdate(BaseModel):
    reason: Optional[str] = None
    is_active: Optional[bool] = None

class BlacklistResponse(BlacklistBase):
    id: int
    date_added: datetime
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)