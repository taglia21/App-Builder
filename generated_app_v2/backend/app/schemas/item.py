"""Item schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = None
    data: Optional[Dict] = None

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    name: str = None
    description: Optional[str] = None
    status: str = None
    data: Optional[Dict] = None

class ItemInDB(ItemBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ItemResponse(ItemInDB):
    pass

class ItemList(BaseModel):
    items: List[ItemResponse]
    total: int
    page: int
    per_page: int
