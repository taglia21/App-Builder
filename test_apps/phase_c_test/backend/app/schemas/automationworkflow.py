"""AutomationWorkflow schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AutomationWorkflowBase(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str
    trigger_condition: str
    action_type: str
    action_value: str
    priority: int
    is_active: bool
    last_execution_time: datetime = None


class AutomationWorkflowCreate(AutomationWorkflowBase):
    pass


class AutomationWorkflowUpdate(BaseModel):
    name: str = None
    description: Optional[str] = None
    trigger_type: str = None
    trigger_condition: str = None
    action_type: str = None
    action_value: str = None
    priority: int = None
    is_active: bool = None
    last_execution_time: datetime = None


class AutomationWorkflowInDB(AutomationWorkflowBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AutomationWorkflowResponse(AutomationWorkflowInDB):
    pass


class AutomationWorkflowList(BaseModel):
    items: List[AutomationWorkflowResponse]
    total: int
    page: int
    per_page: int
