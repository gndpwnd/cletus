"""
schemas/blacklist_schemas.py
Blacklist schemas for validation
"""
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