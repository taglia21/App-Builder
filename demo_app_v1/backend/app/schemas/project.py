"""Project schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = None
    client_name: str
    deadline: datetime.date
    budget: float = None
    priority: int = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: str = None
    description: Optional[str] = None
    status: str = None
    client_name: str = None
    deadline: datetime.date = None
    budget: float = None
    priority: int = None

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
