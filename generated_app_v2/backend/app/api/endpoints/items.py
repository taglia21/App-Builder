"""Item CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.models.user import User
from app.models.item import Item
from app.schemas.item import (
    ItemCreate, 
    ItemUpdate, 
    ItemResponse,
    ItemList
)
from app.crud.item import crud_item
from app.core.auth import get_current_user

router = APIRouter()

@router.get("/", response_model=ItemList)
async def list_items(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all items for current user."""
    skip = (page - 1) * per_page
    items = crud_item.get_multi(db, skip=skip, limit=per_page, user_id=current_user.id)
    total = crud_item.count(db, user_id=current_user.id)
    
    return ItemList(
        items=items,
        total=total,
        page=page,
        per_page=per_page
    )

@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    obj_in: ItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new item."""
    return crud_item.create(db, obj_in=obj_in, user_id=current_user.id)

@router.get("/{id}", response_model=ItemResponse)
async def get_item(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific item."""
    obj = crud_item.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Item not found")
    return obj

@router.put("/{id}", response_model=ItemResponse)
async def update_item(
    id: UUID,
    obj_in: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a item."""
    obj = crud_item.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Item not found")
    return crud_item.update(db, db_obj=obj, obj_in=obj_in)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a item."""
    obj = crud_item.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Item not found")
    crud_item.delete(db, id=id)
