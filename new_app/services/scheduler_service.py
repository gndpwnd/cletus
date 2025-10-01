"""
app/services/scheduler_service.py
Background scheduler with configurable timing and blacklist file watcher
"""
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core.config import settings
from core.database import async_session_maker
from services.scraper_service import ScraperService
from services.blacklist_service import BlacklistService


class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    async def morning_scrape_job(self):
        """Morning scrape job"""
        print(f"[{datetime.now()}] Running morning scrape...")
        
        async with async_session_maker() as db:
            scraper = ScraperService(db)
            session_id = f"morning_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            try:
                await scraper.run_scrape_session(
                    session_id=session_id,
                    categories=None,
                    sources=None
                )
                print(f"[{datetime.now()}] Morning scrape completed")
            except Exception as e:
                print(f"[{datetime.now()}] Morning scrape failed: {e}")
    
    async def evening_scrape_job(self):
        """Evening scrape job"""
        print(f"[{datetime.now()}] Running evening scrape...")
        
        async with async_session_maker() as db:
            scraper = ScraperService(db)
            session_id = f"evening_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            try:
                await scraper.run_scrape_session(
                    session_id=session_id,
                    categories=None,
                    sources=None
                )
                print(f"[{datetime.now()}] Evening scrape completed")
            except Exception as e:
                print(f"[{datetime.now()}] Evening scrape failed: {e}")
    
    async def blacklist_sync_job(self):
        """Check for external blacklist JSON changes and sync to DB"""
        if not settings.WATCH_BLACKLIST_JSON:
            return
        
        async with async_session_maker() as db:
            blacklist_svc = BlacklistService(db)
            
            try:
                changed = await blacklist_svc.check_json_changes()
                if changed:
                    print(f"[{datetime.now()}] Blacklist JSON changed, syncing to DB...")
                    await blacklist_svc.sync_from_json_to_db()
                    print(f"[{datetime.now()}] Blacklist synced")
            except Exception as e:
                print(f"[{datetime.now()}] Blacklist sync error: {e}")
    
    def start(self):
        """Start the scheduler"""
        if self.is_running:
            print("Scheduler is already running")
            return
        
        # Morning scrape - configurable time
        self.scheduler.add_job(
            self.morning_scrape_job,
            trigger=CronTrigger(
                hour=settings.MORNING_SCRAPE_HOUR,
                minute=settings.MORNING_SCRAPE_MINUTE,
                timezone=settings.SCRAPE_TIMEZONE
            ),
            id="morning_scrape",
            name="Morning Scrape Job",
            replace_existing=True
        )
        
        # Evening scrape - configurable time
        self.scheduler.add_job(
            self.evening_scrape_job,
            trigger=CronTrigger(
                hour=settings.EVENING_SCRAPE_HOUR,
                minute=settings.EVENING_SCRAPE_MINUTE,
                timezone=settings.SCRAPE_TIMEZONE
            ),
            id="evening_scrape",
            name="Evening Scrape Job",
            replace_existing=True
        )
        
        # Blacklist file watcher - check every 2 minutes
        if settings.WATCH_BLACKLIST_JSON:
            self.scheduler.add_job(
                self.blacklist_sync_job,
                trigger='interval',
                minutes=2,
                id="blacklist_watcher",
                name="Blacklist File Watcher",
                replace_existing=True
            )
        
        self.scheduler.start()
        self.is_running = True
        
        print(f"Scheduler started:")
        print(f"  - Morning scrape: {settings.MORNING_SCRAPE_HOUR}:{settings.MORNING_SCRAPE_MINUTE:02d} {settings.SCRAPE_TIMEZONE}")
        print(f"  - Evening scrape: {settings.EVENING_SCRAPE_HOUR}:{settings.EVENING_SCRAPE_MINUTE:02d} {settings.SCRAPE_TIMEZONE}")
        if settings.WATCH_BLACKLIST_JSON:
            print(f"  - Blacklist watcher: Every 2 minutes")
    
    def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            print("Scheduler is not running")
            return
        
        self.scheduler.shutdown()
        self.is_running = False
        print("Scheduler stopped")
    
    def get_jobs(self):
        """Get scheduled jobs info"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            })
        return jobs


scheduler_service = SchedulerService()