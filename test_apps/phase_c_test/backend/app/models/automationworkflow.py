"""AutomationWorkflow model."""

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


class AutomationWorkflow(Base):
    __tablename__ = "automation_workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    trigger_type = Column(String(50), nullable=False)
    trigger_condition = Column(Text, nullable=False)
    action_type = Column(String(50), nullable=False)
    action_value = Column(Text, nullable=False)
    priority = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False)
    last_execution_time = Column(DateTime, nullable=True)

    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="automation_workflows")

    def __repr__(self):
        return f"<AutomationWorkflow {self.id}>"
