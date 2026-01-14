"""CustomerInteraction model."""

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


class CustomerInteraction(Base):
    __tablename__ = "customer_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(Integer, nullable=False)
    interaction_type = Column(String(50), nullable=False)
    interaction_details = Column(Text, nullable=True)
    interaction_date = Column(DateTime, nullable=False)
    assigned_agent_id = Column(Integer, nullable=False)
    priority = Column(String(20), nullable=True)
    status = Column(String(50), nullable=False)
    response_time = Column(Float, nullable=True)
    last_updated = Column(DateTime, nullable=True)

    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="customer_interactions")

    def __repr__(self):
        return f"<CustomerInteraction {self.id}>"
