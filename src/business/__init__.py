"""
Business Formation Module

Provides services for automating business formation tasks:
- LLC formation
- EIN application
- Business banking setup
- Domain registration

All services use pluggable provider backends for flexibility.
"""

from src.business.banking import (
    BankingProvider,
    BankingService,
    MercuryProvider,
    MockBankingProvider,
    RelayProvider,
)
from src.business.domain import (
    DomainProvider,
    DomainService,
    GoDaddyProvider,
    MockDomainProvider,
    NamecheapProvider,
)
from src.business.formation import (
    FormationProvider,
    FormationService,
    MockFormationProvider,
    StripeAtlasProvider,
    ZenBusinessProvider,
)
from src.business.models import (
    BankAccountType,
    BankingRequest,
    BankingResult,
    BankingStatus,
    BusinessType,
    DomainRequest,
    DomainResult,
    DomainStatus,
    EINRequest,
    EINResult,
    EINStatus,
    FormationRequest,
    FormationResult,
    FormationState,
    FormationStatus,
)
from src.business.service import BusinessFormationService

__all__ = [
    # Models
    "BusinessType",
    "FormationState",
    "FormationStatus",
    "FormationRequest",
    "FormationResult",
    "EINStatus",
    "EINRequest",
    "EINResult",
    "BankingStatus",
    "BankAccountType",
    "BankingRequest",
    "BankingResult",
    "DomainStatus",
    "DomainRequest",
    "DomainResult",
    # Formation
    "FormationProvider",
    "StripeAtlasProvider",
    "ZenBusinessProvider",
    "MockFormationProvider",
    "FormationService",
    # Domain
    "DomainProvider",
    "NamecheapProvider",
    "GoDaddyProvider",
    "MockDomainProvider",
    "DomainService",
    # Banking
    "BankingProvider",
    "MercuryProvider",
    "RelayProvider",
    "MockBankingProvider",
    "BankingService",
    # Main Service
    "BusinessFormationService",
]
