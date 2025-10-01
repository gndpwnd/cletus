"""
app/services/scraper_service.py
Web scraping service with duplicate detection and appearance tracking
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

from models.models import Article, Blacklist, ScrapeLog
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
                return {"status": "timeout", "articles": 0}
            
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
            log.duration_seconds = time.time() - start_time
            self.db.add(log)
            await self.db.commit()
            
            return {
                "status": "success", 
                "articles": articles_saved,
                "updated": articles_updated
            }
            
        except Exception as e:
            log.status = "error"
            log.error_message = str(e)
            log.duration_seconds = time.time() - start_time
            self.db.add(log)
            await self.db.commit()
            return {"status": "error", "articles": 0, "error": str(e)}
    
    async def run_scrape_session(self, session_id: str, 
                                 categories: Optional[List[str]] = None,
                                 sources: Optional[List[str]] = None):
        """Run a complete scraping session"""
        if categories:
            cats_to_scrape = {k: v for k, v in LINK_DICTIONARIES.items() if k in categories}
        else:
            cats_to_scrape = LINK_DICTIONARIES
        
        async with aiohttp.ClientSession() as session:
            for category, sources_dict in cats_to_scrape.items():
                if sources:
                    sources_dict = {k: v for k, v in sources_dict.items() if k in sources}
                
                for source_name, base_url in sources_dict.items():
                    print(f"Scraping {source_name} from {category}...")
                    result = await self.scrape_source(
                        source_name=source_name,
                        base_url=base_url,
                        category=category,
                        session_id=session_id,
                        session=session
                    )
                    print(f"  -> {result['status']}: {result.get('articles', 0)} new, {result.get('updated', 0)} updated")
                    
                    await asyncio.sleep(settings.SCRAPING_DELAY)
        
        print(f"Scraping session {session_id} completed")