"""CustomerInteraction CRUD endpoints."""

from typing import List
from uuid import UUID

from app.core.auth import get_current_user
from app.crud.customerinteraction import crud_customerinteraction
from app.db.session import get_db
from app.models.customerinteraction import CustomerInteraction
from app.models.user import User
from app.schemas.customerinteraction import (
    CustomerInteractionCreate,
    CustomerInteractionList,
    CustomerInteractionResponse,
    CustomerInteractionUpdate,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/", response_model=CustomerInteractionList)
async def list_customerinteractions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all customerinteractions for current user."""
    skip = (page - 1) * per_page
    items = crud_customerinteraction.get_multi(
        db, skip=skip, limit=per_page, user_id=current_user.id
    )
    total = crud_customerinteraction.count(db, user_id=current_user.id)

    return CustomerInteractionList(items=items, total=total, page=page, per_page=per_page)


@router.post("/", response_model=CustomerInteractionResponse, status_code=status.HTTP_201_CREATED)
async def create_customerinteraction(
    obj_in: CustomerInteractionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new customerinteraction."""
    return crud_customerinteraction.create(db, obj_in=obj_in, user_id=current_user.id)


@router.get("/{id}", response_model=CustomerInteractionResponse)
async def get_customerinteraction(
    id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get a specific customerinteraction."""
    obj = crud_customerinteraction.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="CustomerInteraction not found")
    return obj


@router.put("/{id}", response_model=CustomerInteractionResponse)
async def update_customerinteraction(
    id: UUID,
    obj_in: CustomerInteractionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a customerinteraction."""
    obj = crud_customerinteraction.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="CustomerInteraction not found")
    return crud_customerinteraction.update(db, db_obj=obj, obj_in=obj_in)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customerinteraction(
    id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Delete a customerinteraction."""
    obj = crud_customerinteraction.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="CustomerInteraction not found")
    crud_customerinteraction.delete(db, id=id)
