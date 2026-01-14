"""Customer CRUD endpoints."""

from typing import List
from uuid import UUID

from app.core.auth import get_current_user
from app.crud.customer import crud_customer
from app.db.session import get_db
from app.models.customer import Customer
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerList, CustomerResponse, CustomerUpdate
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/", response_model=CustomerList)
async def list_customers(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all customers for current user."""
    skip = (page - 1) * per_page
    items = crud_customer.get_multi(db, skip=skip, limit=per_page, user_id=current_user.id)
    total = crud_customer.count(db, user_id=current_user.id)

    return CustomerList(items=items, total=total, page=page, per_page=per_page)


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    obj_in: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new customer."""
    return crud_customer.create(db, obj_in=obj_in, user_id=current_user.id)


@router.get("/{id}", response_model=CustomerResponse)
async def get_customer(
    id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get a specific customer."""
    obj = crud_customer.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Customer not found")
    return obj


@router.put("/{id}", response_model=CustomerResponse)
async def update_customer(
    id: UUID,
    obj_in: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a customer."""
    obj = crud_customer.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Customer not found")
    return crud_customer.update(db, db_obj=obj, obj_in=obj_in)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Delete a customer."""
    obj = crud_customer.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Customer not found")
    crud_customer.delete(db, id=id)
