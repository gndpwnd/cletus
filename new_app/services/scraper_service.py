"""
app/services/scraper_service.py
Web scraping service with comprehensive session tracking
"""
import asyncio
import aiohttp
import random
from bs4 import BeautifulSoup
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import urllib.parse
import time

from models.models import Article, Blacklist, ScrapeLog, ScrapeSession
from core.config import settings
from core.sources import LINK_DICTIONARIES

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36"
]

class ScraperService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.blacklist_cache = None
        self.blacklist_cache_time = None
        self.session_stats = {
            'new_articles': 0,
            'updated_articles': 0,
            'total_sources': 0,
            'completed_sources': 0,
            'failed_sources': 0
        }
    
    async def _load_blacklist(self):
        """Load active blacklist patterns into cache"""
        if (self.blacklist_cache is None or 
            self.blacklist_cache_time is None or 
            (datetime.now() - self.blacklist_cache_time).seconds > 300):
            
            result = await self.db.execute(
                select(Blacklist).where(Blacklist.is_active == True)
            )
            self.blacklist_cache = [entry.url_pattern for entry in result.scalars().all()]
            self.blacklist_cache_time = datetime.now()
        
        return self.blacklist_cache
    
    def _is_blacklisted(self, url: str, blacklist: List[str]) -> bool:
        """Check if URL matches any blacklist pattern"""
        return any(url.startswith(pattern) for pattern in blacklist)
    
    async def _check_existing_article(self, headline: str, link: str) -> Optional[Article]:
        """Check if article exists and return it"""
        result = await self.db.execute(
            select(Article).where(
                (Article.headline == headline) | (Article.link == link)
            )
        )
        return result.scalar_one_or_none()
    
    async def _fetch_page(self, url: str, session: aiohttp.ClientSession) -> Optional[str]:
        """Fetch page content with error handling"""
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        
        try:
            async with session.get(url, headers=headers, timeout=settings.SCRAPING_TIMEOUT) as response:
                if response.status == 200:
                    return await response.text()
                return None
        except asyncio.TimeoutError:
            print(f"Timeout fetching {url}")
            return None
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
            return None
    
    def _extract_links(self, html: str, base_url: str, source_name: str, blacklist: List[str]) -> List[dict]:
        """Extract article links from HTML"""
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        
        for a_tag in soup.find_all("a", href=True):
            text = a_tag.get_text(strip=True)
            href = a_tag["href"]
            
            if href == base_url:
                continue
            
            if href.startswith("/"):
                href = base_url.rstrip("/") + href
            
            if not href.startswith("http"):
                continue
            
            if "://" in href[8:]:
                continue
            
            if len(text.split()) < settings.MIN_HEADLINE_WORDS:
                continue
            
            if self._is_blacklisted(href, blacklist):
                continue
            
            parsed = urllib.parse.urlparse(href)
            search_query = f"{parsed.netloc} {text}"
            search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(search_query)}"
            
            articles.append({
                "headline": text,
                "link": href,
                "source": source_name,
                "search_url": search_url,
                "search_query": search_query
            })
        
        return articles
    
    async def scrape_source(self, source_name: str, base_url: str, category: str, 
                           session_id: str, session: aiohttp.ClientSession) -> dict:
        """Scrape a single news source"""
        start_time = time.time()
        blacklist = await self._load_blacklist()
        
        log = ScrapeLog(
            session_id=session_id,
            source=source_name,
            category=category,
            status="started"
        )
        
        try:
            html = await self._fetch_page(base_url, session)
            
            if html is None:
                log.status = "timeout"
                log.error_message = "Failed to fetch page"
                log.duration_seconds = time.time() - start_time
                self.db.add(log)
                await self.db.commit()
                self.session_stats['failed_sources'] += 1
                return {"status": "timeout", "new": 0, "updated": 0}
            
            articles_data = self._extract_links(html, base_url, source_name, blacklist)
            
            articles_saved = 0
            articles_updated = 0
            
            for article_data in articles_data:
                # Check if article already exists
                existing = await self._check_existing_article(
                    article_data["headline"],
                    article_data["link"]
                )
                
                if existing:
                    # Article exists - add new appearance
                    existing.add_appearance()
                    articles_updated += 1
                else:
                    # Create new article
                    article = Article(
                        headline=article_data["headline"],
                        link=article_data["link"],
                        source=source_name,
                        category=category,
                        scrape_session=session_id,
                        is_duplicate=False
                    )
                    article.add_appearance()  # Add first appearance
                    self.db.add(article)
                    articles_saved += 1
            
            await self.db.commit()
            
            log.status = "success"
            log.articles_found = articles_saved
            log.articles_updated = articles_updated
            log.duration_seconds = time.time() - start_time
            self.db.add(log)
            await self.db.commit()
            
            self.session_stats['new_articles'] += articles_saved
            self.session_stats['updated_articles'] += articles_updated
            self.session_stats['completed_sources'] += 1
            
            return {
                "status": "success", 
                "new": articles_saved,
                "updated": articles_updated
            }
            
        except Exception as e:
            log.status = "error"
            log.error_message = str(e)
            log.duration_seconds = time.time() - start_time
            self.db.add(log)
            await self.db.commit()
            self.session_stats['failed_sources'] += 1
            return {"status": "error", "new": 0, "updated": 0, "error": str(e)}
    
    async def run_scrape_session(self, session_id: str, session_type: str,
                                 categories: Optional[List[str]] = None,
                                 sources: Optional[List[str]] = None):
        """Run a complete scraping session with comprehensive tracking"""
        session_start = time.time()
        
        # Reset session stats
        self.session_stats = {
            'new_articles': 0,
            'updated_articles': 0,
            'total_sources': 0,
            'completed_sources': 0,
            'failed_sources': 0
        }
        
        # Determine categories to scrape
        if categories:
            cats_to_scrape = {k: v for k, v in LINK_DICTIONARIES.items() if k in categories}
        else:
            cats_to_scrape = LINK_DICTIONARIES
        
        # Create session record
        scrape_session = ScrapeSession(
            session_id=session_id,
            session_type=session_type,
            status="in_progress"
        )
        scrape_session.set_categories(list(cats_to_scrape.keys()))
        
        # Count total sources
        total_sources = 0
        for sources_dict in cats_to_scrape.values():
            if sources:
                total_sources += len([k for k in sources_dict.keys() if k in sources])
            else:
                total_sources += len(sources_dict)
        
        scrape_session.total_sources = total_sources
        self.session_stats['total_sources'] = total_sources
        
        self.db.add(scrape_session)
        await self.db.commit()
        
        print(f"\n{'='*60}")
        print(f"Starting scrape session: {session_id}")
        print(f"Type: {session_type}")
        print(f"Categories: {', '.join(cats_to_scrape.keys())}")
        print(f"Total sources: {total_sources}")
        print(f"{'='*60}\n")
        
        try:
            async with aiohttp.ClientSession() as session:
                for category, sources_dict in cats_to_scrape.items():
                    if sources:
                        sources_dict = {k: v for k, v in sources_dict.items() if k in sources}
                    
                    print(f"\n[{category}] Scraping {len(sources_dict)} sources...")
                    
                    for source_name, base_url in sources_dict.items():
                        print(f"  → {source_name}...", end=" ")
                        result = await self.scrape_source(
                            source_name=source_name,
                            base_url=base_url,
                            category=category,
                            session_id=session_id,
                            session=session
                        )
                        
                        status_icon = "✓" if result['status'] == 'success' else "✗"
                        print(f"{status_icon} {result['status']}: {result['new']} new, {result['updated']} updated")
                        
                        # Update session progress
                        await self.db.execute(
                            select(ScrapeSession).where(ScrapeSession.session_id == session_id)
                        )
                        await self.db.refresh(scrape_session)
                        scrape_session.completed_sources = self.session_stats['completed_sources']
                        scrape_session.failed_sources = self.session_stats['failed_sources']
                        scrape_session.new_articles = self.session_stats['new_articles']
                        scrape_session.updated_articles = self.session_stats['updated_articles']
                        scrape_session.total_articles_found = self.session_stats['new_articles']
                        await self.db.commit()
                        
                        await asyncio.sleep(settings.SCRAPING_DELAY)
            
            # Mark session as completed
            scrape_session.status = "completed"
            scrape_session.end_time = datetime.now()
            scrape_session.duration_seconds = time.time() - session_start
            await self.db.commit()
            
            print(f"\n{'='*60}")
            print(f"Session {session_id} completed!")
            print(f"Duration: {scrape_session.duration_seconds:.1f}s")
            print(f"New articles: {self.session_stats['new_articles']}")
            print(f"Updated articles: {self.session_stats['updated_articles']}")
            print(f"Sources completed: {self.session_stats['completed_sources']}/{total_sources}")
            print(f"Sources failed: {self.session_stats['failed_sources']}")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"\n✗ Session {session_id} failed: {e}")
            scrape_session.status = "error"
            scrape_session.error_message = str(e)
            scrape_session.end_time = datetime.now()
            scrape_session.duration_seconds = time.time() - session_start
            await self.db.commit()