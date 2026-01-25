"""
Business Formation Module

Provides services for automating business formation tasks:
- LLC formation
- EIN application  
- Business banking setup
- Domain registration

All services use pluggable provider backends for flexibility.
"""

from src.business.models import (
    BusinessType,
    FormationState,
    FormationStatus,
    FormationRequest,
    FormationResult,
    EINStatus,
    EINRequest,
    EINResult,
    BankingStatus,
    BankAccountType,
    BankingRequest,
    BankingResult,
    DomainStatus,
    DomainRequest,
    DomainResult,
)

from src.business.formation import (
    FormationProvider,
    StripeAtlasProvider,
    ZenBusinessProvider,
    MockFormationProvider,
    FormationService,
)

from src.business.domain import (
    DomainProvider,
    NamecheapProvider,
    GoDaddyProvider,
    MockDomainProvider,
    DomainService,
)

from src.business.banking import (
    BankingProvider,
    MercuryProvider,
    RelayProvider,
    MockBankingProvider,
    BankingService,
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
