"""CustomerInteraction schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerInteractionBase(BaseModel):
    customer_id: int
    interaction_type: str
    interaction_details: Optional[str] = None
    interaction_date: datetime
    assigned_agent_id: int
    priority: str = None
    status: str
    response_time: float = None
    last_updated: datetime = None


class CustomerInteractionCreate(CustomerInteractionBase):
    pass


class CustomerInteractionUpdate(BaseModel):
    customer_id: int = None
    interaction_type: str = None
    interaction_details: Optional[str] = None
    interaction_date: datetime = None
    assigned_agent_id: int = None
    priority: str = None
    status: str = None
    response_time: float = None
    last_updated: datetime = None


class CustomerInteractionInDB(CustomerInteractionBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CustomerInteractionResponse(CustomerInteractionInDB):
    pass


class CustomerInteractionList(BaseModel):
    items: List[CustomerInteractionResponse]
    total: int
    page: int
    per_page: int
