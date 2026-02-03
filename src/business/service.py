"""
Business Formation Service

Unified service that orchestrates all business formation components:
- LLC/Business formation
- EIN application
- Business banking
- Domain registration

This is the main entry point for business formation features.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.business.banking import (
    BankingError,
    BankingService,
    MockBankingProvider,
)
from src.business.domain import (
    DomainError,
    DomainService,
    MockDomainProvider,
)
from src.business.formation import (
    FormationError,
    FormationService,
    MockFormationProvider,
)
from src.business.models import (
    BankingRequest,
    BankingStatus,
    BusinessType,
    DomainRequest,
    DomainResult,
    DomainStatus,
    EINRequest,
    EINStatus,
    FormationRequest,
    FormationState,
    FormationStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class BusinessFormationStatus:
    """Overall status of business formation process."""
    user_id: str
    project_id: Optional[str] = None

    # Formation
    formation_id: Optional[str] = None
    formation_status: FormationStatus = FormationStatus.PENDING
    business_name: Optional[str] = None
    business_type: BusinessType = BusinessType.LLC
    state: FormationState = FormationState.DELAWARE

    # EIN
    ein_id: Optional[str] = None
    ein_status: EINStatus = EINStatus.NOT_STARTED
    ein: Optional[str] = None

    # Banking
    banking_id: Optional[str] = None
    banking_status: BankingStatus = BankingStatus.NOT_STARTED
    bank_name: Optional[str] = None

    # Domain
    domain_id: Optional[str] = None
    domain_status: DomainStatus = DomainStatus.PENDING
    domain_name: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "project_id": self.project_id,
            "formation": {
                "id": self.formation_id,
                "status": self.formation_status.value,
                "business_name": self.business_name,
                "business_type": self.business_type.value,
                "state": self.state.value,
            },
            "ein": {
                "id": self.ein_id,
                "status": self.ein_status.value,
                "ein": self.ein,
            },
            "banking": {
                "id": self.banking_id,
                "status": self.banking_status.value,
                "bank_name": self.bank_name,
            },
            "domain": {
                "id": self.domain_id,
                "status": self.domain_status.value,
                "domain_name": self.domain_name,
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @property
    def is_complete(self) -> bool:
        """Check if all formation steps are complete."""
        return (
            self.formation_status == FormationStatus.COMPLETED
            and self.ein_status == EINStatus.RECEIVED
            and self.banking_status == BankingStatus.ACTIVE
            and self.domain_status == DomainStatus.REGISTERED
        )

    @property
    def completion_percentage(self) -> int:
        """Calculate completion percentage."""
        steps = [
            (self.formation_status == FormationStatus.COMPLETED, 30),
            (self.ein_status == EINStatus.RECEIVED, 25),
            (self.banking_status == BankingStatus.ACTIVE, 25),
            (self.domain_status == DomainStatus.REGISTERED, 20),
        ]
        return sum(weight for complete, weight in steps if complete)


class BusinessFormationService:
    """
    Unified business formation service.

    Orchestrates LLC formation, EIN application, banking setup,
    and domain registration into a streamlined workflow.
    """

    def __init__(
        self,
        formation_service: Optional[FormationService] = None,
        domain_service: Optional[DomainService] = None,
        banking_service: Optional[BankingService] = None,
        use_mocks: bool = False,
    ):
        """
        Initialize business formation service.

        Args:
            formation_service: Custom formation service
            domain_service: Custom domain service
            banking_service: Custom banking service
            use_mocks: Use mock providers for testing
        """
        if use_mocks:
            self.formation = FormationService(provider=MockFormationProvider())
            self.domain = DomainService(provider=MockDomainProvider())
            self.banking = BankingService(provider=MockBankingProvider())
        else:
            self.formation = formation_service or FormationService()
            self.domain = domain_service or DomainService()
            self.banking = banking_service or BankingService()

        # Track formation status (in production, use database)
        self._status_cache: Dict[str, BusinessFormationStatus] = {}

    def _get_status(
        self, user_id: str, project_id: Optional[str] = None
    ) -> BusinessFormationStatus:
        """Get or create formation status."""
        key = f"{user_id}:{project_id or 'default'}"
        if key not in self._status_cache:
            self._status_cache[key] = BusinessFormationStatus(
                user_id=user_id,
                project_id=project_id,
            )
        return self._status_cache[key]

    async def start_formation(
        self,
        request: FormationRequest,
    ) -> BusinessFormationStatus:
        """
        Start the business formation process.

        This is the main entry point. It initiates LLC formation
        and returns the tracking status.
        """
        logger.info(f"Starting business formation for {request.business_name}")

        status = self._get_status(request.user_id, request.project_id)
        status.business_name = request.business_name
        status.business_type = request.business_type
        status.state = request.state

        try:
            result = await self.formation.form_llc(request)
            status.formation_id = result.request_id
            status.formation_status = result.status
            status.updated_at = datetime.now(timezone.utc)

            logger.info(f"Formation submitted: {result.request_id}")
        except FormationError as e:
            logger.error(f"Formation failed: {e}")
            status.formation_status = FormationStatus.FAILED

        return status

    async def apply_for_ein(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        request: Optional[EINRequest] = None,
    ) -> BusinessFormationStatus:
        """
        Apply for EIN after formation is approved.

        If request is not provided, uses formation data.
        """
        status = self._get_status(user_id, project_id)

        if status.formation_status not in (FormationStatus.APPROVED, FormationStatus.COMPLETED):
            logger.warning("Formation not yet approved for EIN application")

        if not request:
            # Build request from formation data
            if not status.business_name:
                raise FormationError("No business name found. Complete formation first.")

            request = EINRequest(
                business_name=status.business_name,
                business_type=status.business_type,
                state=status.state,
                responsible_party_name="",  # Would come from user profile
                street_address="",
                city="",
                state_address=status.state.value,
                zip_code="",
                user_id=user_id,
                formation_id=status.formation_id,
            )

        try:
            result = await self.formation.apply_for_ein(request)
            status.ein_id = result.request_id
            status.ein_status = result.status
            if result.ein:
                status.ein = result.ein
            status.updated_at = datetime.now(timezone.utc)

            logger.info(f"EIN application submitted: {result.request_id}")
        except FormationError as e:
            logger.error(f"EIN application failed: {e}")
            status.ein_status = EINStatus.FAILED

        return status

    async def setup_banking(
        self,
        request: BankingRequest,
    ) -> BusinessFormationStatus:
        """
        Set up business banking after formation and EIN.

        Banking typically requires a valid EIN.
        """
        status = self._get_status(request.user_id, request.formation_id)

        if status.ein_status != EINStatus.RECEIVED:
            logger.warning("EIN not yet received for banking setup")

        try:
            result = await self.banking.apply_for_account(request)
            status.banking_id = result.request_id
            status.banking_status = result.status
            status.bank_name = result.bank_name
            status.updated_at = datetime.now(timezone.utc)

            logger.info(f"Banking application submitted: {result.request_id}")
        except BankingError as e:
            logger.error(f"Banking setup failed: {e}")
            status.banking_status = BankingStatus.REJECTED

        return status

    async def register_domain(
        self,
        request: DomainRequest,
    ) -> BusinessFormationStatus:
        """
        Register a domain for the business.

        Can be done in parallel with other steps.
        """
        status = self._get_status(request.user_id, request.project_id)

        try:
            result = await self.domain.register_domain(request)
            status.domain_id = result.request_id
            status.domain_status = result.status
            status.domain_name = result.domain_name
            status.updated_at = datetime.now(timezone.utc)

            logger.info(f"Domain registered: {result.domain_name}")
        except DomainError as e:
            logger.error(f"Domain registration failed: {e}")
            status.domain_status = DomainStatus.FAILED

        return status

    async def check_domain_availability(
        self,
        domain_name: str,
    ) -> DomainResult:
        """Check if a domain is available."""
        return await self.domain.check_domain(domain_name)

    async def suggest_domains(
        self,
        keyword: str,
        tlds: Optional[List[str]] = None,
    ) -> List[DomainResult]:
        """Get domain suggestions based on keyword."""
        return await self.domain.suggest_domains(keyword, tlds)

    async def get_status(
        self,
        user_id: str,
        project_id: Optional[str] = None,
    ) -> BusinessFormationStatus:
        """
        Get current formation status.

        Refreshes status from providers if needed.
        """
        status = self._get_status(user_id, project_id)

        # Refresh from providers
        try:
            if status.formation_id and status.formation_status not in (
                FormationStatus.COMPLETED, FormationStatus.FAILED
            ):
                result = await self.formation.get_status(status.formation_id)
                status.formation_status = result.status
                if result.ein:
                    status.ein = result.ein
                    status.ein_status = EINStatus.RECEIVED
        except FormationError:
            pass

        try:
            if status.ein_id and status.ein_status not in (
                EINStatus.RECEIVED, EINStatus.FAILED
            ):
                result = await self.formation.get_ein_status(status.ein_id)
                status.ein_status = result.status
                if result.ein:
                    status.ein = result.ein
        except FormationError:
            pass

        try:
            if status.banking_id and status.banking_status not in (
                BankingStatus.ACTIVE, BankingStatus.REJECTED, BankingStatus.CLOSED
            ):
                result = await self.banking.get_application_status(status.banking_id)
                status.banking_status = result.status
        except BankingError:
            pass

        try:
            if status.domain_name:
                result = await self.domain.get_status(status.domain_name)
                status.domain_status = result.status
        except DomainError:
            pass

        status.updated_at = datetime.now(timezone.utc)
        return status

    def estimate_costs(
        self,
        state: FormationState = FormationState.DELAWARE,
        business_type: BusinessType = BusinessType.LLC,
        domain_name: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Estimate total costs for business formation.

        Returns breakdown of all costs.
        """
        options = options or {
            "registered_agent": True,
            "operating_agreement": True,
            "expedited": False,
        }

        formation_cost = self.formation.estimate_cost(
            state, business_type, options
        )

        domain_cost = {"total": 0}
        if domain_name:
            domain_cost = self.domain.estimate_cost(domain_name, 1)

        return {
            "formation": formation_cost,
            "domain": domain_cost,
            "banking": {"total": 0},  # Banking is typically free
            "total": formation_cost["total"] + domain_cost["total"],
            "currency": "usd",
            "formatted_total": f"${(formation_cost['total'] + domain_cost['total']) / 100:.2f}",
        }


# Convenience functions
def create_business_service(use_mocks: bool = False) -> BusinessFormationService:
    """Create a business formation service with default settings."""
    return BusinessFormationService(use_mocks=use_mocks)
