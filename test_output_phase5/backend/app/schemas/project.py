"""Project schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class ProjectBase(BaseModel):
    name: str
    status: str

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: str = None
    status: str = None

class ProjectInDB(ProjectBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ProjectResponse(ProjectInDB):
    pass

class ProjectList(BaseModel):
    items: List[ProjectResponse]
    total: int
    page: int
    per_page: int
