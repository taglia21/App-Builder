"""
Business Banking Providers

Pluggable providers for business bank account setup.
Supports Mercury, Relay, and mock providers.
"""

import logging
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Optional

from src.business.models import (
    BankAccountType,
    BankingRequest,
    BankingResult,
    BankingStatus,
)

logger = logging.getLogger(__name__)


class BankingError(Exception):
    """Base exception for banking errors."""
    pass


class BankingProvider(ABC):
    """Abstract base class for banking providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @abstractmethod
    async def submit_application(
        self, request: BankingRequest
    ) -> BankingResult:
        """Submit bank account application."""
        pass

    @abstractmethod
    async def get_application_status(
        self, request_id: str
    ) -> BankingResult:
        """Get application status."""
        pass

    @abstractmethod
    async def get_account_info(
        self, account_id: str
    ) -> BankingResult:
        """Get account information."""
        pass


class MercuryProvider(BankingProvider):
    """
    Mercury Bank guided flow for business bank account setup.

    NOTE: Mercury does not expose a public API for onboarding new business
    accounts. This provider is a guided flow — it returns the signup URL
    and instructs the user to apply at mercury.com. No HTTP requests are
    made to any Mercury endpoint.

    Mercury is popular for startups and tech companies.
    """

    # Internal store for guided-flow references keyed by request_id
    _applications: Dict[str, BankingResult] = {}

    def __init__(
        self,
        api_key: Optional[str] = None,
        sandbox: bool = True,
    ):
        self.api_key = api_key or os.getenv("MERCURY_API_KEY")
        self.sandbox = sandbox

    @property
    def name(self) -> str:
        return "mercury"

    def _get_headers(self) -> Dict[str, str]:
        """Get API headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def submit_application(
        self, request: BankingRequest
    ) -> BankingResult:
        """
        Guided flow for Mercury business bank account application.

        Mercury does not expose a public API for onboarding new business bank
        accounts. This is a guided flow — no HTTP requests are made. The user
        must complete the application manually at mercury.com.
        """
        request_id = str(uuid.uuid4())
        mercury_url = "https://mercury.com/sign-up"

        logger.info(
            f"Mercury guided flow initiated for {request.business_name}. "
            f"User must complete application manually at {mercury_url}."
        )

        result = BankingResult(
            request_id=request_id,
            status=BankingStatus.APPLICATION_PENDING,
            bank_name="Mercury",
            account_type=request.account_type,
            provider=self.name,
            provider_reference=mercury_url,
            dashboard_url=mercury_url,
            message=(
                "Mercury does not provide a public API for new account onboarding. "
                "Please complete your business bank account application manually at "
                f"{mercury_url}. You will need your EIN, formation documents, and "
                "owner identification to apply."
            ),
            verification_steps=[
                "Create a Mercury account at mercury.com/sign-up",
                "Provide your EIN and business formation documents",
                "Complete identity verification",
                "Submit business documentation for review",
            ],
        )

        MercuryProvider._applications[request_id] = result
        return result

    async def get_application_status(
        self, request_id: str
    ) -> BankingResult:
        """
        Return status for a Mercury guided flow application.

        Mercury does not provide a public onboarding status API. Application
        status must be checked at app.mercury.com. If the request_id was
        created by this provider, the stored result is returned; otherwise a
        helpful placeholder is returned.
        """
        mercury_dashboard = "https://app.mercury.com"

        if request_id in MercuryProvider._applications:
            return MercuryProvider._applications[request_id]

        return BankingResult(
            request_id=request_id,
            status=BankingStatus.APPLICATION_PENDING,
            bank_name="Mercury",
            account_type=BankAccountType.CHECKING,
            provider=self.name,
            provider_reference=mercury_dashboard,
            dashboard_url=mercury_dashboard,
            message=(
                "Mercury does not provide a public application status API. "
                f"Please check the status of your application at {mercury_dashboard}."
            ),
        )

    async def get_account_info(
        self, account_id: str
    ) -> BankingResult:
        """
        Return account info for a Mercury account.

        Mercury does not provide a public account info API for third-party
        applications. Account details are available directly at app.mercury.com.
        """
        mercury_dashboard = "https://app.mercury.com"

        return BankingResult(
            request_id=account_id,
            status=BankingStatus.ACTIVE,
            bank_name="Mercury",
            account_type=BankAccountType.CHECKING,
            dashboard_url=mercury_dashboard,
            provider=self.name,
            provider_reference=account_id,
            message=(
                "Mercury account details are available at your Mercury dashboard. "
                f"Please visit {mercury_dashboard} to view your account information."
            ),
        )


class RelayProvider(BankingProvider):
    """
    Relay Bank guided flow for business bank account setup.

    NOTE: Relay does not expose a public API for onboarding new business
    accounts. This provider is a guided flow — it returns the signup URL
    and instructs the user to apply at relayfi.com. No HTTP requests are
    made to any Relay endpoint.

    Relay is another popular choice for startups.
    """

    # Internal store for guided-flow references keyed by request_id
    _applications: Dict[str, BankingResult] = {}

    def __init__(
        self,
        api_key: Optional[str] = None,
        sandbox: bool = True,
    ):
        self.api_key = api_key or os.getenv("RELAY_API_KEY")
        self.sandbox = sandbox

    @property
    def name(self) -> str:
        return "relay"

    def _get_headers(self) -> Dict[str, str]:
        """Get API headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def submit_application(
        self, request: BankingRequest
    ) -> BankingResult:
        """
        Guided flow for Relay business bank account application.

        Relay does not expose a public API for onboarding new business bank
        accounts. This is a guided flow — no HTTP requests are made. The user
        must complete the application manually at relayfi.com.
        """
        request_id = str(uuid.uuid4())
        relay_url = "https://relayfi.com/sign-up"

        logger.info(
            f"Relay guided flow initiated for {request.business_name}. "
            f"User must complete application manually at {relay_url}."
        )

        result = BankingResult(
            request_id=request_id,
            status=BankingStatus.APPLICATION_PENDING,
            bank_name="Relay",
            account_type=request.account_type,
            provider=self.name,
            provider_reference=relay_url,
            dashboard_url=relay_url,
            message=(
                "Relay does not provide a public API for new account onboarding. "
                "Please complete your business bank account application manually at "
                f"{relay_url}. You will need your EIN, formation documents, and "
                "owner identification to apply."
            ),
            verification_steps=[
                "Create a Relay account at relayfi.com/sign-up",
                "Provide your EIN and business formation documents",
                "Complete identity verification",
                "Submit business documentation for review",
            ],
        )

        RelayProvider._applications[request_id] = result
        return result

    async def get_application_status(
        self, request_id: str
    ) -> BankingResult:
        """
        Return status for a Relay guided flow application.

        Relay does not provide a public onboarding status API. Application
        status must be checked at app.relayfi.com. If the request_id was
        created by this provider, the stored result is returned; otherwise a
        helpful placeholder is returned.
        """
        relay_dashboard = "https://app.relayfi.com"

        if request_id in RelayProvider._applications:
            return RelayProvider._applications[request_id]

        return BankingResult(
            request_id=request_id,
            status=BankingStatus.APPLICATION_PENDING,
            bank_name="Relay",
            account_type=BankAccountType.CHECKING,
            provider=self.name,
            provider_reference=relay_dashboard,
            dashboard_url=relay_dashboard,
            message=(
                "Relay does not provide a public application status API. "
                f"Please check the status of your application at {relay_dashboard}."
            ),
        )

    async def get_account_info(
        self, account_id: str
    ) -> BankingResult:
        """
        Return account info for a Relay account.

        Relay does not provide a public account info API for third-party
        applications. Account details are available directly at app.relayfi.com.
        """
        relay_dashboard = "https://app.relayfi.com"

        return BankingResult(
            request_id=account_id,
            status=BankingStatus.ACTIVE,
            bank_name="Relay",
            account_type=BankAccountType.CHECKING,
            dashboard_url=relay_dashboard,
            provider=self.name,
            provider_reference=account_id,
            message=(
                "Relay account details are available at your Relay dashboard. "
                f"Please visit {relay_dashboard} to view your account information."
            ),
        )


class MockBankingProvider(BankingProvider):
    """Mock provider for testing."""

    def __init__(self):
        self._applications: Dict[str, BankingResult] = {}

    @property
    def name(self) -> str:
        return "mock"

    async def submit_application(
        self, request: BankingRequest
    ) -> BankingResult:
        """Submit mock bank application."""
        request_id = str(uuid.uuid4())

        result = BankingResult(
            request_id=request_id,
            status=BankingStatus.APPLICATION_PENDING,
            bank_name="Mock Bank",
            account_type=request.account_type,
            provider=self.name,
            provider_reference=f"MOCK-{request_id[:8]}",
            dashboard_url="https://mock.bank.dev/dashboard",
            message="Mock application submitted",
            verification_steps=["Mock verification"],
        )

        self._applications[request_id] = result
        return result

    async def get_application_status(
        self, request_id: str
    ) -> BankingResult:
        """Get mock application status."""
        if request_id not in self._applications:
            raise BankingError(f"Application not found: {request_id}")
        return self._applications[request_id]

    async def approve_application(
        self, request_id: str
    ) -> BankingResult:
        """Approve a mock application (for testing)."""
        if request_id not in self._applications:
            raise BankingError(f"Application not found: {request_id}")

        result = self._applications[request_id]
        result.status = BankingStatus.ACTIVE
        result.account_number = "****1234"
        result.routing_number = "123456789"
        result.verification_steps = []
        result.message = "Account is active"
        result.updated_at = datetime.now(timezone.utc)

        return result

    async def get_account_info(
        self, account_id: str
    ) -> BankingResult:
        """Get mock account info."""
        if account_id in self._applications:
            return self._applications[account_id]

        return BankingResult(
            request_id=account_id,
            status=BankingStatus.ACTIVE,
            bank_name="Mock Bank",
            account_type=BankAccountType.CHECKING,
            account_number="****5678",
            routing_number="987654321",
            dashboard_url="https://mock.bank.dev/dashboard",
            provider=self.name,
        )


class BankingService:
    """High-level service for business banking."""

    def __init__(
        self,
        provider: Optional[BankingProvider] = None,
        default_provider: str = "mercury",
    ):
        self.default_provider = default_provider

        if provider:
            self.provider = provider
        else:
            provider_name = os.getenv("BANKING_PROVIDER", default_provider)
            self.provider = self._create_provider(provider_name)

    def _create_provider(self, name: str) -> BankingProvider:
        """Create provider by name."""
        providers = {
            "mercury": MercuryProvider,
            "relay": RelayProvider,
            "mock": MockBankingProvider,
        }

        if name not in providers:
            raise BankingError(f"Unknown provider: {name}")

        return providers[name]()

    async def apply_for_account(
        self, request: BankingRequest
    ) -> BankingResult:
        """Apply for a business bank account."""
        logger.info(f"Starting bank account application for {request.business_name}")
        return await self.provider.submit_application(request)

    async def get_application_status(
        self, request_id: str
    ) -> BankingResult:
        """Get bank application status."""
        return await self.provider.get_application_status(request_id)

    async def get_account(
        self, account_id: str
    ) -> BankingResult:
        """Get account information."""
        return await self.provider.get_account_info(account_id)
