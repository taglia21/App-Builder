"""AutomationWorkflow CRUD endpoints."""

from typing import List
from uuid import UUID

from app.core.auth import get_current_user
from app.crud.automationworkflow import crud_automationworkflow
from app.db.session import get_db
from app.models.automationworkflow import AutomationWorkflow
from app.models.user import User
from app.schemas.automationworkflow import (
    AutomationWorkflowCreate,
    AutomationWorkflowList,
    AutomationWorkflowResponse,
    AutomationWorkflowUpdate,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/", response_model=AutomationWorkflowList)
async def list_automationworkflows(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all automationworkflows for current user."""
    skip = (page - 1) * per_page
    items = crud_automationworkflow.get_multi(
        db, skip=skip, limit=per_page, user_id=current_user.id
    )
    total = crud_automationworkflow.count(db, user_id=current_user.id)

    return AutomationWorkflowList(items=items, total=total, page=page, per_page=per_page)


@router.post("/", response_model=AutomationWorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_automationworkflow(
    obj_in: AutomationWorkflowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new automationworkflow."""
    return crud_automationworkflow.create(db, obj_in=obj_in, user_id=current_user.id)


@router.get("/{id}", response_model=AutomationWorkflowResponse)
async def get_automationworkflow(
    id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get a specific automationworkflow."""
    obj = crud_automationworkflow.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="AutomationWorkflow not found")
    return obj


@router.put("/{id}", response_model=AutomationWorkflowResponse)
async def update_automationworkflow(
    id: UUID,
    obj_in: AutomationWorkflowUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a automationworkflow."""
    obj = crud_automationworkflow.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="AutomationWorkflow not found")
    return crud_automationworkflow.update(db, db_obj=obj, obj_in=obj_in)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_automationworkflow(
    id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Delete a automationworkflow."""
    obj = crud_automationworkflow.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="AutomationWorkflow not found")
    crud_automationworkflow.delete(db, id=id)
