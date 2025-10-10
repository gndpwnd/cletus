"""
main.py
FastAPI News Aggregation Application - Enhanced with CSS loader
"""
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from pathlib import Path
import asyncio
import json
from datetime import datetime

from api import articles, blacklist, scraper, analysis
from core.config import settings
from core.database import init_db, async_session_maker
from services.scheduler_service import scheduler_service
from services.blacklist_service import BlacklistService

# Import CSS loader
from css_loader import get_css_files

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

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
    
    # Start change watcher task
    asyncio.create_task(watch_for_changes())
    print("✓ Change watcher started")
    
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

# Add CSS loader to template context
@app.middleware("http")
async def add_css_context(request: Request, call_next):
    """Add CSS files to all template contexts"""
    response = await call_next(request)
    return response

# Custom template response that includes CSS files
def render_template(template_name: str, request: Request, **context):
    """Render template with CSS files automatically included"""
    context["request"] = request
    context["css_files"] = get_css_files()
    return templates.TemplateResponse(template_name, context)

# Include API routers
app.include_router(articles.router, prefix="/api/articles", tags=["Articles"])
app.include_router(blacklist.router, prefix="/api/blacklist", tags=["Blacklist"])
app.include_router(scraper.router, prefix="/api/scraper", tags=["Scraper"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Change watcher background task
async def watch_for_changes():
    """Watch for database and blacklist changes"""
    from sqlalchemy import select, func
    from models.models import Article, Blacklist
    
    last_article_count = 0
    last_blacklist_count = 0
    last_check = datetime.now()
    
    while True:
        try:
            await asyncio.sleep(2)
            
            async with async_session_maker() as db:
                result = await db.execute(select(func.count(Article.id)))
                current_article_count = result.scalar()
                
                result = await db.execute(
                    select(func.count(Blacklist.id)).where(Blacklist.is_active == True)
                )
                current_blacklist_count = result.scalar()
                
                changes = {}
                
                if current_article_count != last_article_count:
                    changes["articles"] = {
                        "count": current_article_count,
                        "new": current_article_count - last_article_count
                    }
                    last_article_count = current_article_count
                
                if current_blacklist_count != last_blacklist_count:
                    changes["blacklist"] = {
                        "count": current_blacklist_count,
                        "new": current_blacklist_count - last_blacklist_count
                    }
                    last_blacklist_count = current_blacklist_count
                
                if changes:
                    await manager.broadcast({
                        "type": "database_update",
                        "timestamp": datetime.now().isoformat(),
                        "changes": changes
                    })
        
        except Exception as e:
            print(f"Error in change watcher: {e}")
            await asyncio.sleep(5)

# Frontend routes - Updated to use render_template
@app.get("/")
async def root(request: Request):
    """Serve dashboard homepage"""
    return render_template("index.html", request)

@app.get("/articles")
async def articles_page(request: Request):
    """Serve articles page"""
    return render_template("articles.html", request)

@app.get("/scraper")
async def scraper_page(request: Request):
    """Serve scraper page"""
    return render_template("scraper.html", request)

@app.get("/blacklist")
async def blacklist_page(request: Request):
    """Serve blacklist page"""
    return render_template("blacklist.html", request)

@app.get("/analysis")
async def analysis_page(request: Request):
    """Serve analysis page"""
    return render_template("analysis.html", request)

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
            "Article analysis and trending topics",
            "Real-time updates via WebSocket",
            "Lazy loading and infinite scroll"
        ],
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "api": "/api/info",
            "websocket": "/ws"
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