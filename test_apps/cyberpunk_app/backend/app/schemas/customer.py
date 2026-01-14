"""Customer schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerBase(BaseModel):
    name: str
    email: str
    phone: str
    company: str = None
    industry: str = None
    website: str = None
    lead_score: int = None
    last_contact_date: datetime = None
    notes: Optional[str] = None
    preferred_contact_method: str = None
    customer_segment: str = None
    total_purchases: float = None
    lifetime_value: float = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str = None
    email: str = None
    phone: str = None
    company: str = None
    industry: str = None
    website: str = None
    lead_score: int = None
    last_contact_date: datetime = None
    notes: Optional[str] = None
    preferred_contact_method: str = None
    customer_segment: str = None
    total_purchases: float = None
    lifetime_value: float = None


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
