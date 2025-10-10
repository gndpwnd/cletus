"""
app/models/models.py
SQLAlchemy database models with enhanced session tracking
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import json
from datetime import datetime

class Article(Base):
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True, index=True)
    headline = Column(String, nullable=False, index=True)
    link = Column(String, nullable=False, unique=True, index=True)
    source = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    date_scraped = Column(DateTime(timezone=True), server_default=func.now())
    date_published = Column(DateTime(timezone=True), nullable=True)
    
    # Track when article appeared in different scrape sessions
    appearances = Column(Text, default="[]")  # JSON array of timestamps as text
    
    # Analysis fields
    is_duplicate = Column(Boolean, default=False)
    is_selected = Column(Boolean, default=False)
    priority_score = Column(Float, nullable=True)
    analysis_notes = Column(Text, nullable=True)
    
    # Scrape info
    scrape_session = Column(String, nullable=True)
    
    def add_appearance(self):
        """Add current timestamp to appearances list"""
        try:
            appearances_list = json.loads(self.appearances)
        except (json.JSONDecodeError, TypeError):
            appearances_list = []
        
        appearances_list.append(datetime.now().isoformat())
        self.appearances = json.dumps(appearances_list)
    
    def get_appearances(self):
        """Get list of appearance timestamps"""
        try:
            return json.loads(self.appearances)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def __repr__(self):
        return f"<Article(id={self.id}, headline='{self.headline[:50]}...')>"


class Blacklist(Base):
    __tablename__ = "blacklist"
    
    id = Column(Integer, primary_key=True, index=True)
    url_pattern = Column(String, nullable=False, unique=True, index=True)
    date_added = Column(DateTime(timezone=True), server_default=func.now())
    reason = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Blacklist(pattern='{self.url_pattern}')>"


class ScrapeSession(Base):
    """Track overall scraping sessions"""
    __tablename__ = "scrape_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=False, unique=True, index=True)
    session_type = Column(String, nullable=False)  # manual, morning, evening
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False, default="started")  # started, in_progress, completed, error
    
    # Categories scraped (JSON array)
    categories = Column(Text, default="[]")
    
    # Summary stats
    total_sources = Column(Integer, default=0)
    completed_sources = Column(Integer, default=0)
    failed_sources = Column(Integer, default=0)
    total_articles_found = Column(Integer, default=0)
    new_articles = Column(Integer, default=0)
    updated_articles = Column(Integer, default=0)
    
    # Duration
    duration_seconds = Column(Float, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Relationship to individual source logs
    logs = relationship("ScrapeLog", back_populates="session", cascade="all, delete-orphan")
    
    def get_categories(self):
        """Get list of categories"""
        try:
            return json.loads(self.categories)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_categories(self, categories_list):
        """Set categories as JSON"""
        self.categories = json.dumps(categories_list)
    
    def __repr__(self):
        return f"<ScrapeSession(session_id='{self.session_id}', status='{self.status}')>"


class ScrapeLog(Base):
    """Track individual source scraping within a session"""
    __tablename__ = "scrape_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey('scrape_sessions.session_id'), nullable=False, index=True)
    source = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False)  # success, timeout, error
    articles_found = Column(Integer, default=0)
    articles_updated = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    scrape_time = Column(DateTime(timezone=True), server_default=func.now())
    duration_seconds = Column(Float, nullable=True)
    
    # Relationship back to session
    session = relationship("ScrapeSession", back_populates="logs")
    
    def __repr__(self):
        return f"<ScrapeLog(session={self.session_id}, source='{self.source}')>"