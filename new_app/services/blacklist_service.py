"""
app/services/blacklist_service.py
Blacklist management with auto-sync and file watching
"""
import json
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Blacklist
from core.config import settings


class BlacklistService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.json_dir = Path(settings.BLACKLIST_DIR)
        self.json_dir.mkdir(exist_ok=True)
        self._last_json_mtime = None
    
    def _get_json_filename(self) -> Path:
        """Get current blacklist JSON filename"""
        date_str = datetime.now().strftime('%Y_%m_%d')
        return self.json_dir / f"blklst_{date_str}.json"
    
    def _get_latest_json_file(self) -> Optional[Path]:
        """Get the most recent blacklist JSON file"""
        json_files = sorted(self.json_dir.glob("blklst_*.json"), reverse=True)
        return json_files[0] if json_files else None
    
    def _load_json_blacklist(self, file_path: Optional[Path] = None) -> List[str]:
        """Load blacklist from JSON file"""
        if file_path is None:
            file_path = self._get_latest_json_file()
        
        if not file_path or not file_path.exists():
            return []
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return data.get("blacklisted_links", [])
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading blacklist JSON: {e}")
            return []
    
    def _save_json_blacklist(self, patterns: List[str]):
        """Save blacklist to JSON file"""
        json_file = self._get_json_filename()
        
        data = {
            "blacklisted_links": sorted(list(set(patterns)))
        }
        
        try:
            with open(json_file, 'w') as f:
                json.dump(data, f, indent=4)
            self._last_json_mtime = json_file.stat().st_mtime
            print(f"Blacklist saved to {json_file}")
        except IOError as e:
            print(f"Error saving blacklist JSON: {e}")
    
    async def check_json_changes(self) -> bool:
        """Check if JSON file has been modified externally"""
        if not settings.WATCH_BLACKLIST_JSON:
            return False
        
        json_file = self._get_latest_json_file()
        if not json_file:
            return False
        
        try:
            current_mtime = json_file.stat().st_mtime
            if self._last_json_mtime is None:
                self._last_json_mtime = current_mtime
                return False
            
            if current_mtime > self._last_json_mtime:
                self._last_json_mtime = current_mtime
                return True
            return False
        except OSError:
            return False
    
    async def sync_from_json_to_db(self):
        """Sync JSON blacklist to database"""
        json_patterns = self._load_json_blacklist()
        added_count = 0
        
        for pattern in json_patterns:
            result = await self.db.execute(
                select(Blacklist).where(Blacklist.url_pattern == pattern)
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                db_entry = Blacklist(
                    url_pattern=pattern,
                    is_active=True,
                    reason="Imported from JSON"
                )
                self.db.add(db_entry)
                added_count += 1
            elif not existing.is_active:
                existing.is_active = True
                added_count += 1
        
        await self.db.commit()
        print(f"Synced {added_count} patterns from JSON to database")
    
    async def sync_from_db_to_json(self):
        """Sync database blacklist to JSON"""
        result = await self.db.execute(
            select(Blacklist).where(Blacklist.is_active == True)
        )
        db_entries = result.scalars().all()
        
        patterns = [entry.url_pattern for entry in db_entries]
        self._save_json_blacklist(patterns)
        print(f"Synced {len(patterns)} patterns from database to JSON")
    
    async def add_pattern(self, pattern: str, reason: Optional[str] = None) -> Blacklist:
        """Add pattern to both DB and JSON"""
        result = await self.db.execute(
            select(Blacklist).where(Blacklist.url_pattern == pattern)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            if not existing.is_active:
                existing.is_active = True
                existing.reason = reason or existing.reason
                await self.db.commit()
                await self.db.refresh(existing)
            db_entry = existing
        else:
            db_entry = Blacklist(
                url_pattern=pattern,
                is_active=True,
                reason=reason
            )
            self.db.add(db_entry)
            await self.db.commit()
            await self.db.refresh(db_entry)
        
        # Auto-sync to JSON if enabled
        if settings.AUTO_SYNC_BLACKLIST:
            await self.sync_from_db_to_json()
        
        return db_entry
    
    async def remove_pattern(self, pattern: str):
        """Remove pattern from both DB and JSON"""
        result = await self.db.execute(
            select(Blacklist).where(Blacklist.url_pattern == pattern)
        )
        entry = result.scalar_one_or_none()
        
        if entry:
            entry.is_active = False
            await self.db.commit()
        
        # Auto-sync to JSON if enabled
        if settings.AUTO_SYNC_BLACKLIST:
            await self.sync_from_db_to_json()
    
    async def get_all_active(self) -> List[str]:
        """Get all active blacklist patterns"""
        result = await self.db.execute(
            select(Blacklist).where(Blacklist.is_active == True)
        )
        entries = result.scalars().all()
        return [entry.url_pattern for entry in entries]
    
    def is_blacklisted(self, url: str, patterns: List[str]) -> bool:
        """Check if URL matches any blacklist pattern"""
        return any(url.startswith(pattern) for pattern in patterns)
    
    async def export_blacklist(self) -> Path:
        """Export current database blacklist to JSON (manual trigger)"""
        await self.sync_from_db_to_json()
        return self._get_json_filename()
    
    async def cleanup_old_json_files(self, keep_days: int = 30):
        """Remove old JSON blacklist files"""
        cutoff = datetime.now().timestamp() - (keep_days * 86400)
        
        for json_file in self.json_dir.glob("blklst_*.json"):
            if json_file.stat().st_mtime < cutoff:
                try:
                    json_file.unlink()
                    print(f"Deleted old blacklist file: {json_file}")
                except OSError as e:
                    print(f"Error deleting {json_file}: {e}")