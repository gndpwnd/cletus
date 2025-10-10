"""
app/core/config.py
Application configuration with schedule customization
"""
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Cletus News Aggregator"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./cletus.db"
    
    # Scraping
    SCRAPE_COOLDOWN_MINUTES: int = 5    
    SCRAPING_TIMEOUT: int = 10
    SCRAPING_MAX_RETRIES: int = 3
    SCRAPING_DELAY: float = 1.0
    
    # History retention
    HISTORY_RETENTION_DAYS: int = 10
    BLACKLIST_RETENTION_DAYS: int = 30
    
    # Analysis
    MIN_HEADLINE_WORDS: int = 5
    DUPLICATE_CHECK_ENABLED: bool = True
    
    # Scheduling - Configurable times
    MORNING_SCRAPE_HOUR: int = 9
    MORNING_SCRAPE_MINUTE: int = 45
    EVENING_SCRAPE_HOUR: int = 21
    EVENING_SCRAPE_MINUTE: int = 45
    SCRAPE_TIMEZONE: str = "America/New_York"
    
    # Blacklist
    BLACKLIST_DIR: str = "blacklists"
    AUTO_SYNC_BLACKLIST: bool = True  # Auto-sync to JSON on changes
    WATCH_BLACKLIST_JSON: bool = True  # Watch for external JSON changes
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()