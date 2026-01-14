"""Lead schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class LeadBase(BaseModel):
    lead_id: str
    customer_name: str
    email: str
    phone: str
    company: str = None
    source: str = None
    status: str = None
    notes: Optional[str] = None
    last_contacted: datetime = None
    lead_score: float = None
    priority: str = None
    assigned_agent: str = None
    conversion_status: bool = None
    conversion_date: datetime = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    lead_id: str = None
    customer_name: str = None
    email: str = None
    phone: str = None
    company: str = None
    source: str = None
    status: str = None
    notes: Optional[str] = None
    last_contacted: datetime = None
    lead_score: float = None
    priority: str = None
    assigned_agent: str = None
    conversion_status: bool = None
    conversion_date: datetime = None


class LeadInDB(LeadBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LeadResponse(LeadInDB):
    pass


class LeadList(BaseModel):
    items: List[LeadResponse]
    total: int
    page: int
    per_page: int
