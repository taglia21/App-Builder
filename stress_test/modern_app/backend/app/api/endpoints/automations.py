"""Automation CRUD endpoints."""

from typing import List
from uuid import UUID

from app.core.auth import get_current_user
from app.crud.automation import crud_automation
from app.db.session import get_db
from app.models.automation import Automation
from app.models.user import User
from app.schemas.automation import (
    AutomationCreate,
    AutomationList,
    AutomationResponse,
    AutomationUpdate,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/", response_model=AutomationList)
async def list_automations(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all automations for current user."""
    skip = (page - 1) * per_page
    items = crud_automation.get_multi(db, skip=skip, limit=per_page, user_id=current_user.id)
    total = crud_automation.count(db, user_id=current_user.id)

    return AutomationList(items=items, total=total, page=page, per_page=per_page)


@router.post("/", response_model=AutomationResponse, status_code=status.HTTP_201_CREATED)
async def create_automation(
    obj_in: AutomationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new automation."""
    return crud_automation.create(db, obj_in=obj_in, user_id=current_user.id)


@router.get("/{id}", response_model=AutomationResponse)
async def get_automation(
    id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get a specific automation."""
    obj = crud_automation.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Automation not found")
    return obj


@router.put("/{id}", response_model=AutomationResponse)
async def update_automation(
    id: UUID,
    obj_in: AutomationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a automation."""
    obj = crud_automation.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Automation not found")
    return crud_automation.update(db, db_obj=obj, obj_in=obj_in)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_automation(
    id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Delete a automation."""
    obj = crud_automation.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Automation not found")
    crud_automation.delete(db, id=id)
