"""Project CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.models.user import User
from app.models.project import Project
from app.schemas.project import (
    ProjectCreate, 
    ProjectUpdate, 
    ProjectResponse,
    ProjectList
)
from app.crud.project import crud_project
from app.core.auth import get_current_user

router = APIRouter()

@router.get("/", response_model=ProjectList)
async def list_projects(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all projects for current user."""
    skip = (page - 1) * per_page
    items = crud_project.get_multi(db, skip=skip, limit=per_page, user_id=current_user.id)
    total = crud_project.count(db, user_id=current_user.id)
    
    return ProjectList(
        items=items,
        total=total,
        page=page,
        per_page=per_page
    )

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    obj_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new project."""
    return crud_project.create(db, obj_in=obj_in, user_id=current_user.id)

@router.get("/{id}", response_model=ProjectResponse)
async def get_project(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific project."""
    obj = crud_project.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Project not found")
    return obj

@router.put("/{id}", response_model=ProjectResponse)
async def update_project(
    id: UUID,
    obj_in: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a project."""
    obj = crud_project.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Project not found")
    return crud_project.update(db, db_obj=obj, obj_in=obj_in)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a project."""
    obj = crud_project.get_by_user(db, id=id, user_id=current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Project not found")
    crud_project.delete(db, id=id)
