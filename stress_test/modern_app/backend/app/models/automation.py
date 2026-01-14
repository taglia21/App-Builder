"""Automation model."""

import uuid
from datetime import datetime

from app.db.base_class import Base
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class Automation(Base):
    __tablename__ = "automations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    workflow_type = Column(String(50), nullable=False)
    trigger_condition = Column(Text, nullable=True)
    action_steps = Column(Text, nullable=True)
    status = Column(String(50), nullable=False)
    last_run_time = Column(DateTime, nullable=True)
    next_run_time = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False)
    assignee_id = Column(Integer, nullable=True)
    customer_segment = Column(String(50), nullable=True)

    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="automations")

    def __repr__(self):
        return f"<Automation {self.id}>"
