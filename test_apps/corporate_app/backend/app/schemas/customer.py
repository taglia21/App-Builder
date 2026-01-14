"""Customer schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerBase(BaseModel):
    email: str
    name: str
    phone: str = None
    company: str = None
    industry: str = None
    website: str = None
    country: str = None
    state: str = None
    city: str = None
    lead_score: int = None
    last_contact_date: Optional[datetime] = None
    next_contact_date: Optional[datetime] = None
    notes: Optional[str] = None
    stage: str = None
    source: str = None
    preferred_contact_method: str = None
    preferred_contact_time: str = None
    automation_status: str = None
    ai_analysis: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    email: str = None
    name: str = None
    phone: str = None
    company: str = None
    industry: str = None
    website: str = None
    country: str = None
    state: str = None
    city: str = None
    lead_score: int = None
    last_contact_date: Optional[datetime] = None
    next_contact_date: Optional[datetime] = None
    notes: Optional[str] = None
    stage: str = None
    source: str = None
    preferred_contact_method: str = None
    preferred_contact_time: str = None
    automation_status: str = None
    ai_analysis: Optional[str] = None


class CustomerInDB(CustomerBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CustomerResponse(CustomerInDB):
    pass


class CustomerList(BaseModel):
    items: List[CustomerResponse]
    total: int
    page: int
    per_page: int
