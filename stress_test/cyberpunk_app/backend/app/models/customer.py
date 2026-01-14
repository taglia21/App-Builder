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
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    company = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    website = Column(String(255), nullable=True)
    industry = Column(String(100), nullable=True)
    customer_segment = Column(String(100), nullable=True)
    last_contact_date = Column(DateTime, nullable=True)
    lead_score = Column(Float, nullable=True)
    preferred_contact_method = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    account_manager = Column(String(100), nullable=True)
    ai_analysis_status = Column(String(50), nullable=True)
    last_ai_update = Column(DateTime, nullable=True)
    customer_lifetime_value = Column(Float, nullable=True)

    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="customers")

    def __repr__(self):
        return f"<Customer {self.id}>"
