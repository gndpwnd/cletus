"""
main.py
FastAPI News Aggregation Application - Main entry point with template support
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from pathlib import Path

from api import articles, blacklist, scraper, analysis
from core.config import settings
from core.database import init_db
from services.scheduler_service import scheduler_service
from services.blacklist_service import BlacklistService
from core.database import async_session_maker

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    print("Starting Cletus News Aggregator...")
    
    # Initialize database
    await init_db()
    print("✓ Database initialized")
    
    # Sync blacklist from JSON to DB on startup
    async with async_session_maker() as db:
        blacklist_svc = BlacklistService(db)
        await blacklist_svc.sync_from_json_to_db()
        print("✓ Blacklist synced from JSON to database")
    
    # Start scheduler
    scheduler_service.start()
    print("✓ Scheduler started")
    print(f"\nApplication running at http://{settings.HOST}:{settings.PORT}")
    print(f"API Documentation: http://{settings.HOST}:{settings.PORT}/docs\n")
    
    yield
    
    # Shutdown
    print("\nShutting down...")
    scheduler_service.stop()
    print("✓ Scheduler stopped")

app = FastAPI(
    title="Cletus News Aggregator",
    description="Modular news scraping and analysis platform",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
Path("static/css").mkdir(parents=True, exist_ok=True)
Path("static/js").mkdir(parents=True, exist_ok=True)
Path("templates").mkdir(exist_ok=True)
Path("blacklists").mkdir(exist_ok=True)
Path("logs").mkdir(exist_ok=True)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Include API routers
app.include_router(articles.router, prefix="/api/articles", tags=["Articles"])
app.include_router(blacklist.router, prefix="/api/blacklist", tags=["Blacklist"])
app.include_router(scraper.router, prefix="/api/scraper", tags=["Scraper"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])

# Frontend routes
@app.get("/")
async def root(request: Request):
    """Serve dashboard homepage"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/articles")
async def articles_page(request: Request):
    """Serve articles page"""
    return templates.TemplateResponse("articles.html", {"request": request})

@app.get("/scraper")
async def scraper_page(request: Request):
    """Serve scraper page"""
    return templates.TemplateResponse("scraper.html", {"request": request})

@app.get("/blacklist")
async def blacklist_page(request: Request):
    """Serve blacklist page"""
    return templates.TemplateResponse("blacklist.html", {"request": request})

@app.get("/analysis")
async def analysis_page(request: Request):
    """Serve analysis page"""
    return templates.TemplateResponse("analysis.html", {"request": request})

# API endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    jobs = []
    if scheduler_service.is_running:
        jobs = scheduler_service.get_jobs()
    
    return {
        "status": "healthy",
        "scheduler_running": scheduler_service.is_running,
        "scheduled_jobs": jobs
    }

@app.get("/api/info")
async def api_info():
    """API information"""
    return {
        "app": settings.APP_NAME,
        "version": "2.0.0",
        "database": "SQLite with async support",
        "features": [
            "Automated scraping (twice daily, configurable)",
            "Manual scraping on-demand with category/source filtering",
            "Duplicate detection and article appearance tracking",
            "Blacklist management (dual JSON + DB with auto-sync)",
            "Article analysis and prioritization",
            "Trending topics detection",
            "Source reliability metrics"
        ],
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "api": "/api/info"
        },
        "schedule": {
            "morning": f"{settings.MORNING_SCRAPE_HOUR}:{settings.MORNING_SCRAPE_MINUTE:02d} {settings.SCRAPE_TIMEZONE}",
            "evening": f"{settings.EVENING_SCRAPE_HOUR}:{settings.EVENING_SCRAPE_MINUTE:02d} {settings.SCRAPE_TIMEZONE}"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )