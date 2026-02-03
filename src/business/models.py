"""
Business Formation Models

Pydantic models and enums for business formation services.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class BusinessType(str, Enum):
    """Types of business entities."""
    LLC = "llc"
    CORPORATION = "corporation"
    S_CORP = "s_corp"
    C_CORP = "c_corp"
    SOLE_PROPRIETORSHIP = "sole_proprietorship"
    PARTNERSHIP = "partnership"
    NONPROFIT = "nonprofit"


class FormationState(str, Enum):
    """US states for LLC formation."""
    DELAWARE = "DE"
    WYOMING = "WY"
    NEVADA = "NV"
    FLORIDA = "FL"
    TEXAS = "TX"
    CALIFORNIA = "CA"
    NEW_YORK = "NY"
    WASHINGTON = "WA"
    COLORADO = "CO"
    ARIZONA = "AZ"
    GEORGIA = "GA"
    ILLINOIS = "IL"
    MASSACHUSETTS = "MA"
    NEW_JERSEY = "NJ"
    PENNSYLVANIA = "PA"


class FormationStatus(str, Enum):
    """Status of LLC/business formation."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


class FormationRequest(BaseModel):
    """Request for LLC/business formation."""
    business_name: str = Field(..., min_length=1, max_length=200)
    business_type: BusinessType = BusinessType.LLC
    state: FormationState = FormationState.DELAWARE

    # Contact info
    owner_name: str = Field(..., min_length=1)
    owner_email: str
    owner_phone: Optional[str] = None

    # Address
    street_address: str
    city: str
    state_address: str
    zip_code: str
    country: str = "US"

    # Business details
    description: str = ""
    purpose: str = "Any lawful purpose"

    # Options
    registered_agent: bool = True
    operating_agreement: bool = True
    expedited: bool = False

    # Metadata
    user_id: str
    project_id: Optional[str] = None


class FormationResult(BaseModel):
    """Result of LLC/business formation."""
    request_id: str
    status: FormationStatus

    # Business info
    business_name: str
    business_type: BusinessType
    state: FormationState

    # Formation details
    ein: Optional[str] = None
    formation_date: Optional[datetime] = None
    certificate_url: Optional[str] = None
    operating_agreement_url: Optional[str] = None

    # Provider info
    provider: str
    provider_reference: Optional[str] = None

    # Status info
    message: Optional[str] = None
    estimated_completion: Optional[datetime] = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EINStatus(str, Enum):
    """Status of EIN application."""
    NOT_STARTED = "not_started"
    PENDING = "pending"
    SUBMITTED = "submitted"
    RECEIVED = "received"
    FAILED = "failed"


class EINRequest(BaseModel):
    """Request for EIN application."""
    business_name: str
    business_type: BusinessType
    state: FormationState

    # Responsible party
    responsible_party_name: str
    responsible_party_ssn: Optional[str] = None  # Encrypted in practice
    responsible_party_itin: Optional[str] = None

    # Business address
    street_address: str
    city: str
    state_address: str
    zip_code: str

    # Business details
    principal_activity: str = "Software development"
    date_started: Optional[datetime] = None
    expected_employees: int = 0

    # Metadata
    user_id: str
    formation_id: Optional[str] = None


class EINResult(BaseModel):
    """Result of EIN application."""
    request_id: str
    status: EINStatus

    # EIN info
    ein: Optional[str] = None
    business_name: str

    # Status
    message: Optional[str] = None
    confirmation_letter_url: Optional[str] = None

    # Provider
    provider: str
    provider_reference: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BankingStatus(str, Enum):
    """Status of bank account setup."""
    NOT_STARTED = "not_started"
    APPLICATION_PENDING = "application_pending"
    VERIFICATION_REQUIRED = "verification_required"
    APPROVED = "approved"
    ACTIVE = "active"
    REJECTED = "rejected"
    CLOSED = "closed"


class BankAccountType(str, Enum):
    """Types of bank accounts."""
    CHECKING = "checking"
    SAVINGS = "savings"
    MONEY_MARKET = "money_market"


class BankingRequest(BaseModel):
    """Request for business bank account."""
    business_name: str
    ein: str

    # Business info
    business_type: BusinessType
    state: FormationState
    formation_date: datetime

    # Contact
    owner_name: str
    owner_email: str
    owner_phone: str

    # Address
    street_address: str
    city: str
    state_address: str
    zip_code: str

    # Account preferences
    account_type: BankAccountType = BankAccountType.CHECKING
    estimated_monthly_revenue: Optional[int] = None

    # Metadata
    user_id: str
    formation_id: Optional[str] = None


class BankingResult(BaseModel):
    """Result of bank account setup."""
    request_id: str
    status: BankingStatus

    # Account info
    bank_name: str
    account_type: BankAccountType
    account_number: Optional[str] = None  # Masked
    routing_number: Optional[str] = None

    # Access
    dashboard_url: Optional[str] = None

    # Status
    message: Optional[str] = None
    verification_steps: List[str] = Field(default_factory=list)

    # Provider
    provider: str
    provider_reference: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DomainStatus(str, Enum):
    """Status of domain registration."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    PENDING = "pending"
    REGISTERED = "registered"
    TRANSFER_PENDING = "transfer_pending"
    EXPIRED = "expired"
    FAILED = "failed"


class DomainRequest(BaseModel):
    """Request for domain registration."""
    domain_name: str = Field(..., min_length=1, max_length=253)

    # Registrant info
    registrant_name: str
    registrant_email: str
    registrant_phone: Optional[str] = None

    # Address
    street_address: str
    city: str
    state: str
    zip_code: str
    country: str = "US"

    # Options
    privacy_protection: bool = True
    auto_renew: bool = True
    years: int = Field(default=1, ge=1, le=10)

    # DNS
    nameservers: List[str] = Field(default_factory=list)

    # Metadata
    user_id: str
    project_id: Optional[str] = None


class DomainResult(BaseModel):
    """Result of domain registration."""
    request_id: str
    status: DomainStatus

    # Domain info
    domain_name: str
    registrar: str

    # Registration details
    registered_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    auto_renew: bool = True
    privacy_protection: bool = True

    # DNS
    nameservers: List[str] = Field(default_factory=list)

    # Status
    message: Optional[str] = None
    management_url: Optional[str] = None

    # Provider
    provider: str
    provider_reference: Optional[str] = None

    # Pricing
    price_paid: Optional[int] = None  # in cents
    renewal_price: Optional[int] = None  # in cents

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Pricing constants
FORMATION_PRICES = {
    FormationState.DELAWARE: {
        BusinessType.LLC: 8900,  # $89
        BusinessType.CORPORATION: 14900,  # $149
    },
    FormationState.WYOMING: {
        BusinessType.LLC: 10200,  # $102
        BusinessType.CORPORATION: 15200,  # $152
    },
}

EXPEDITED_FEE = 5000  # $50
REGISTERED_AGENT_ANNUAL = 12500  # $125/year
