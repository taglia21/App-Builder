"""Automation schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AutomationBase(BaseModel):
    name: str
    description: Optional[str] = None
    workflow_type: str
    trigger_condition: Optional[str] = None
    action_steps: Optional[str] = None
    status: str
    last_run_time: Optional[datetime] = None
    next_run_time: Optional[datetime] = None
    is_active: bool
    assignee_id: Optional[int] = None
    customer_segment: Optional[str] = None


class AutomationCreate(AutomationBase):
    pass


class AutomationUpdate(BaseModel):
    name: str = None
    description: Optional[str] = None
    workflow_type: str = None
    trigger_condition: Optional[str] = None
    action_steps: Optional[str] = None
    status: str = None
    last_run_time: Optional[datetime] = None
    next_run_time: Optional[datetime] = None
    is_active: bool = None
    assignee_id: Optional[int] = None
    customer_segment: Optional[str] = None


class AutomationInDB(AutomationBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AutomationResponse(AutomationInDB):
    pass


class AutomationList(BaseModel):
    items: List[AutomationResponse]
    total: int
    page: int
    per_page: int
