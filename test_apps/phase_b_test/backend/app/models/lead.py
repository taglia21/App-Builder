"""Lead model."""

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


class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(String(255), nullable=False)
    customer_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    company = Column(String(255), nullable=True)
    source = Column(String(100), nullable=True)
    status = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    last_contacted = Column(DateTime, nullable=True)
    lead_score = Column(Float, nullable=True)
    priority = Column(String(50), nullable=True)
    assigned_agent = Column(String(255), nullable=True)
    conversion_status = Column(Boolean, nullable=True)
    conversion_date = Column(DateTime, nullable=True)

    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="leads")

    def __repr__(self):
        return f"<Lead {self.id}>"
