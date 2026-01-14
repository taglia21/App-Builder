"""Base CRUD operations."""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID

from app.db.base_class import Base
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: UUID) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id).first()

    def get_by_user(self, db: Session, id: UUID, user_id: UUID) -> Optional[ModelType]:
        return (
            db.query(self.model).filter(self.model.id == id, self.model.user_id == user_id).first()
        )

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, user_id: Optional[UUID] = None
    ) -> List[ModelType]:
        query = db.query(self.model)
        if user_id:
            query = query.filter(self.model.user_id == user_id)
        return query.offset(skip).limit(limit).all()

    def count(self, db: Session, user_id: Optional[UUID] = None) -> int:
        query = db.query(func.count(self.model.id))
        if user_id:
            query = query.filter(self.model.user_id == user_id)
        return query.scalar()

    def create(self, db: Session, *, obj_in: CreateSchemaType, user_id: UUID) -> ModelType:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data, user_id=user_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: ModelType, obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, id: UUID) -> ModelType:
        obj = db.query(self.model).get(id)
        db.delete(obj)
        db.commit()
        return obj
