"""Customer schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerBase(BaseModel):
    email: str
    first_name: str = None
    last_name: str = None
    company: str = None
    phone: str = None
    website: str = None
    industry: str = None
    customer_segment: str = None
    last_contact_date: datetime = None
    lead_score: float = None
    preferred_contact_method: str = None
    notes: Optional[str] = None
    account_manager: str = None
    ai_analysis_status: str = None
    last_ai_update: datetime = None
    customer_lifetime_value: float = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    email: str = None
    first_name: str = None
    last_name: str = None
    company: str = None
    phone: str = None
    website: str = None
    industry: str = None
    customer_segment: str = None
    last_contact_date: datetime = None
    lead_score: float = None
    preferred_contact_method: str = None
    notes: Optional[str] = None
    account_manager: str = None
    ai_analysis_status: str = None
    last_ai_update: datetime = None
    customer_lifetime_value: float = None


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
