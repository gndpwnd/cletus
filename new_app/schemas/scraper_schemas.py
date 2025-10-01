"""Scraper schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List

class ScrapeRequest(BaseModel):
    session_type: str = Field("manual", description="morning, evening, or manual")
    categories: Optional[List[str]] = None
    sources: Optional[List[str]] = None

class ScrapeResponse(BaseModel):
    message: str
    session_id: str
    status: str

class ScrapeStatusResponse(BaseModel):
    session_id: str
    status: str
    total_sources: int
    completed_sources: int
    failed_sources: int
    total_articles: int
    logs: Optional[List[dict]] = None