"""Customer model."""

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


class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    company = Column(String(255), nullable=True)
    industry = Column(String(100), nullable=True)
    website = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    lead_score = Column(Integer, nullable=True)
    last_contact_date = Column(DateTime, nullable=True)
    next_contact_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    stage = Column(String(50), nullable=True)
    source = Column(String(100), nullable=True)
    preferred_contact_method = Column(String(50), nullable=True)
    preferred_contact_time = Column(String(50), nullable=True)
    automation_status = Column(String(50), nullable=True)
    ai_analysis = Column(Text, nullable=True)

    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="customers")

    def __repr__(self):
        return f"<Customer {self.id}>"
