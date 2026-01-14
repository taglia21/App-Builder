"""Lead CRUD endpoints."""

from typing import List
from uuid import UUID

from app.core.auth import get_current_user
from app.crud.lead import crud_lead
from app.db.session import get_db
from app.models.lead import Lead
from app.models.user import User
from app.schemas.lead import LeadCreate, LeadList, LeadResponse, LeadUpdate
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/", response_model=LeadList)
async def list_leads(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all leads for current user."""
    skip = (page - 1) * per_page
    items = crud_lead.get_multi(db, skip=skip, limit=per_page, user_id=current_user.id)
    total = crud_lead.count(db, user_id=current_user.id)

    return LeadList(items=items, total=total, page=page, per_page=per_page)


@router.post("/", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    obj_in: LeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new lead."""
    return crud_lead.create(db, obj_in=obj_in, user_id=current_user.id)


@router.get("/{id}", response_model=LeadResponse)
async def get_lead(
    id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get a specific lead."""
    obj = crud_lead.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Lead not found")
    return obj


@router.put("/{id}", response_model=LeadResponse)
async def update_lead(
    id: UUID,
    obj_in: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a lead."""
    obj = crud_lead.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Lead not found")
    return crud_lead.update(db, db_obj=obj, obj_in=obj_in)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Delete a lead."""
    obj = crud_lead.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Lead not found")
    crud_lead.delete(db, id=id)
