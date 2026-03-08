"""
LLC/Business Formation Providers

Pluggable providers for business formation services.
Supports Stripe Atlas, ZenBusiness, and mock providers for testing.
"""

import logging
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from src.business.models import (
    EXPEDITED_FEE,
    FORMATION_PRICES,
    REGISTERED_AGENT_ANNUAL,
    BusinessType,
    EINRequest,
    EINResult,
    EINStatus,
    FormationRequest,
    FormationResult,
    FormationState,
    FormationStatus,
)

logger = logging.getLogger(__name__)


class FormationError(Exception):
    """Base exception for formation errors."""
    pass


class FormationProvider(ABC):
    """Abstract base class for formation providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @abstractmethod
    async def submit_formation(
        self, request: FormationRequest
    ) -> FormationResult:
        """Submit LLC/business formation request."""
        pass

    @abstractmethod
    async def get_formation_status(
        self, request_id: str
    ) -> FormationResult:
        """Get status of formation request."""
        pass

    @abstractmethod
    async def submit_ein_application(
        self, request: EINRequest
    ) -> EINResult:
        """Submit EIN application."""
        pass

    @abstractmethod
    async def get_ein_status(
        self, request_id: str
    ) -> EINResult:
        """Get status of EIN application."""
        pass

    @abstractmethod
    def get_pricing(
        self,
        state: FormationState,
        business_type: BusinessType,
        options: Dict[str, Any]
    ) -> Dict[str, int]:
        """Get pricing breakdown for formation."""
        pass


class StripeAtlasProvider(FormationProvider):
    """
    Stripe Atlas guided flow for business formation.

    NOTE: Stripe Atlas does NOT have a public API for submitting formation
    applications — it is a manual web form at https://stripe.com/atlas.
    This provider is a guided flow: it returns the signup URL and instructs
    the user to complete the application there. No HTTP requests are made
    to any Stripe Atlas endpoint.
    """

    # Internal store for tracking guided-flow references keyed by request_id
    _pending: Dict[str, FormationResult] = {}

    def __init__(
        self,
        api_key: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        sandbox: bool = True,
    ):
        self.api_key = api_key or os.getenv("STRIPE_ATLAS_API_KEY")
        self.webhook_secret = webhook_secret or os.getenv("STRIPE_ATLAS_WEBHOOK_SECRET")
        self.sandbox = sandbox

        # Stripe Atlas pricing (as of 2024)
        self.base_price = 50000  # $500
        self.includes = ["delaware_llc", "ein", "bank_account", "one_year_registered_agent"]

    @property
    def name(self) -> str:
        return "stripe_atlas"

    async def submit_formation(
        self, request: FormationRequest
    ) -> FormationResult:
        """
        Guided flow for Stripe Atlas business formation.

        Stripe Atlas does not expose a public API for submitting formation
        applications. This is a guided flow — no HTTP requests are made.
        The user must complete the application manually at stripe.com/atlas.
        """
        request_id = str(uuid.uuid4())
        atlas_url = "https://stripe.com/atlas"

        logger.info(
            f"Stripe Atlas guided flow initiated for {request.business_name}. "
            f"User must complete application manually at {atlas_url}."
        )

        result = FormationResult(
            request_id=request_id,
            status=FormationStatus.PENDING,
            business_name=request.business_name,
            business_type=request.business_type,
            state=request.state,
            provider=self.name,
            provider_reference=atlas_url,
            message=(
                "Stripe Atlas does not have a public API for submitting formation "
                "applications. Please complete your application manually at "
                f"{atlas_url}. Stripe Atlas includes Delaware LLC formation, EIN, "
                "a Mercury bank account, and one year of registered agent service for $500."
            ),
            estimated_completion=datetime.now(timezone.utc) + timedelta(days=5),
        )

        # Store locally so status checks can return a helpful response
        StripeAtlasProvider._pending[request_id] = result
        return result

    async def get_formation_status(
        self, request_id: str
    ) -> FormationResult:
        """
        Return status for a Stripe Atlas guided flow.

        Stripe Atlas does not have a public status API. Formation status must
        be checked manually at stripe.com/atlas. If the request_id was created
        by this provider, the original pending result is returned; otherwise a
        helpful placeholder is returned.
        """
        atlas_url = "https://stripe.com/atlas"

        if request_id in StripeAtlasProvider._pending:
            return StripeAtlasProvider._pending[request_id]

        # Unknown request_id — return an honest fallback
        return FormationResult(
            request_id=request_id,
            status=FormationStatus.PENDING,
            business_name="",
            business_type=BusinessType.LLC,
            state=FormationState.DE,
            provider=self.name,
            provider_reference=atlas_url,
            message=(
                "Stripe Atlas does not provide a status API. "
                f"Please check the status of your application at {atlas_url}."
            ),
        )

    async def submit_ein_application(
        self, request: EINRequest
    ) -> EINResult:
        """
        Submit EIN application through Atlas.

        Note: Stripe Atlas includes EIN in the base package.
        """
        # Atlas handles EIN automatically
        return EINResult(
            request_id=str(uuid.uuid4()),
            status=EINStatus.PENDING,
            business_name=request.business_name,
            message="EIN is included with Stripe Atlas formation",
            provider=self.name,
        )

    async def get_ein_status(
        self, request_id: str
    ) -> EINResult:
        """
        Return EIN status for a Stripe Atlas guided flow.

        EIN is included in the Stripe Atlas package and is obtained as part of
        the formation process at stripe.com/atlas. No API call is made.
        """
        formation = await self.get_formation_status(request_id)

        return EINResult(
            request_id=request_id,
            status=EINStatus.RECEIVED if formation.ein else EINStatus.PENDING,
            ein=formation.ein,
            business_name=formation.business_name,
            provider=self.name,
            message=(
                "EIN is included with Stripe Atlas formation. "
                "Check your EIN status at https://stripe.com/atlas."
            ),
        )

    def get_pricing(
        self,
        state: FormationState,
        business_type: BusinessType,
        options: Dict[str, Any]
    ) -> Dict[str, int]:
        """Stripe Atlas has flat pricing."""
        return {
            "base": self.base_price,
            "registered_agent": 0,  # Included
            "ein": 0,  # Included
            "bank_account": 0,  # Included
            "total": self.base_price,
        }


class ZenBusinessProvider(FormationProvider):
    """
    ZenBusiness guided flow for business formation.

    NOTE: ZenBusiness does not expose a public API for programmatic formation
    submissions. This provider is a guided flow — it returns the signup URL
    and instructs the user to complete the application at zenbusiness.com.
    No HTTP requests are made to any ZenBusiness endpoint.

    More flexible pricing than Stripe Atlas.
    """

    # Internal store for guided-flow references keyed by request_id
    _pending: Dict[str, FormationResult] = {}
    _eins: Dict[str, EINResult] = {}

    def __init__(
        self,
        api_key: Optional[str] = None,
        sandbox: bool = True,
    ):
        self.api_key = api_key or os.getenv("ZENBUSINESS_API_KEY")
        self.sandbox = sandbox

    @property
    def name(self) -> str:
        return "zenbusiness"

    async def submit_formation(
        self, request: FormationRequest
    ) -> FormationResult:
        """
        Guided flow for ZenBusiness business formation.

        ZenBusiness does not provide a public API for programmatic formation
        submissions. This is a guided flow — no HTTP requests are made.
        The user must complete the application manually at zenbusiness.com.
        """
        request_id = str(uuid.uuid4())
        zenbusiness_url = "https://www.zenbusiness.com/form-an-llc/"

        logger.info(
            f"ZenBusiness guided flow initiated for {request.business_name}. "
            f"User must complete application manually at {zenbusiness_url}."
        )

        result = FormationResult(
            request_id=request_id,
            status=FormationStatus.PENDING,
            business_name=request.business_name,
            business_type=request.business_type,
            state=request.state,
            provider=self.name,
            provider_reference=zenbusiness_url,
            message=(
                "ZenBusiness does not provide a public API for formation submissions. "
                "Please complete your formation application manually at "
                f"{zenbusiness_url}. ZenBusiness handles state filing, registered agent "
                "service, and operating agreement preparation."
            ),
            estimated_completion=datetime.now(timezone.utc) + timedelta(days=3 if request.expedited else 7),
        )

        ZenBusinessProvider._pending[request_id] = result
        return result

    async def get_formation_status(
        self, request_id: str
    ) -> FormationResult:
        """
        Return status for a ZenBusiness guided flow.

        ZenBusiness does not provide a public status API. Formation status must
        be checked manually at zenbusiness.com. If the request_id was created
        by this provider, the original pending result is returned; otherwise a
        helpful placeholder is returned.
        """
        zenbusiness_url = "https://www.zenbusiness.com"

        if request_id in ZenBusinessProvider._pending:
            return ZenBusinessProvider._pending[request_id]

        return FormationResult(
            request_id=request_id,
            status=FormationStatus.PENDING,
            business_name="",
            business_type=BusinessType.LLC,
            state=FormationState.DE,
            provider=self.name,
            provider_reference=zenbusiness_url,
            message=(
                "ZenBusiness does not provide a status API. "
                f"Please check the status of your order at {zenbusiness_url}."
            ),
        )

    async def submit_ein_application(
        self, request: EINRequest
    ) -> EINResult:
        """
        Guided flow for EIN application through ZenBusiness.

        ZenBusiness does not provide a public API for EIN applications.
        This is a guided flow — no HTTP requests are made. The user must
        request EIN service as part of their ZenBusiness order at zenbusiness.com.
        """
        request_id = str(uuid.uuid4())
        zenbusiness_ein_url = "https://www.zenbusiness.com/ein/"

        logger.info(
            f"ZenBusiness EIN guided flow initiated for {request.business_name}. "
            f"User must complete EIN request at {zenbusiness_ein_url}."
        )

        result = EINResult(
            request_id=request_id,
            status=EINStatus.PENDING,
            business_name=request.business_name,
            message=(
                "ZenBusiness does not provide a public API for EIN applications. "
                "Please request EIN service as part of your ZenBusiness formation order at "
                f"{zenbusiness_ein_url}."
            ),
            provider=self.name,
            provider_reference=zenbusiness_ein_url,
        )

        ZenBusinessProvider._eins[request_id] = result
        return result

    async def get_ein_status(
        self, request_id: str
    ) -> EINResult:
        """
        Return EIN status for a ZenBusiness guided flow.

        ZenBusiness does not provide a public EIN status API. Status must be
        checked at zenbusiness.com. If the request_id was created by this
        provider, the stored result is returned; otherwise a helpful placeholder.
        """
        zenbusiness_url = "https://www.zenbusiness.com"

        if request_id in ZenBusinessProvider._eins:
            return ZenBusinessProvider._eins[request_id]

        return EINResult(
            request_id=request_id,
            status=EINStatus.PENDING,
            business_name="",
            provider=self.name,
            provider_reference=zenbusiness_url,
            message=(
                "ZenBusiness does not provide a public EIN status API. "
                f"Please check the status of your EIN request at {zenbusiness_url}."
            ),
        )

    def get_pricing(
        self,
        state: FormationState,
        business_type: BusinessType,
        options: Dict[str, Any]
    ) -> Dict[str, int]:
        """Get ZenBusiness pricing."""
        base_prices = FORMATION_PRICES.get(state, {}).get(business_type, 8900)

        total = base_prices
        breakdown = {"base": base_prices}

        if options.get("registered_agent"):
            breakdown["registered_agent"] = REGISTERED_AGENT_ANNUAL
            total += REGISTERED_AGENT_ANNUAL

        if options.get("expedited"):
            breakdown["expedited"] = EXPEDITED_FEE
            total += EXPEDITED_FEE

        if options.get("operating_agreement"):
            breakdown["operating_agreement"] = 0  # Included in base

        breakdown["total"] = total
        return breakdown


class MockFormationProvider(FormationProvider):
    """Mock provider for testing."""

    def __init__(self):
        self._formations: Dict[str, FormationResult] = {}
        self._eins: Dict[str, EINResult] = {}

    @property
    def name(self) -> str:
        return "mock"

    async def submit_formation(
        self, request: FormationRequest
    ) -> FormationResult:
        """Submit mock formation."""
        request_id = str(uuid.uuid4())

        result = FormationResult(
            request_id=request_id,
            status=FormationStatus.SUBMITTED,
            business_name=request.business_name,
            business_type=request.business_type,
            state=request.state,
            provider=self.name,
            provider_reference=f"MOCK-{request_id[:8]}",
            message="Mock formation submitted",
            estimated_completion=datetime.now(timezone.utc) + timedelta(days=3),
        )

        self._formations[request_id] = result
        return result

    async def get_formation_status(
        self, request_id: str
    ) -> FormationResult:
        """Get mock formation status."""
        if request_id not in self._formations:
            raise FormationError(f"Formation not found: {request_id}")
        return self._formations[request_id]

    async def complete_formation(
        self, request_id: str, ein: str = "12-3456789"
    ) -> FormationResult:
        """Complete a mock formation (for testing)."""
        if request_id not in self._formations:
            raise FormationError(f"Formation not found: {request_id}")

        result = self._formations[request_id]
        result.status = FormationStatus.COMPLETED
        result.ein = ein
        result.formation_date = datetime.now(timezone.utc)
        result.certificate_url = f"https://mock.ignara.app/certs/{request_id}"
        result.updated_at = datetime.now(timezone.utc)

        return result

    async def submit_ein_application(
        self, request: EINRequest
    ) -> EINResult:
        """Submit mock EIN application."""
        request_id = str(uuid.uuid4())

        result = EINResult(
            request_id=request_id,
            status=EINStatus.SUBMITTED,
            business_name=request.business_name,
            message="Mock EIN application submitted",
            provider=self.name,
            provider_reference=f"MOCK-EIN-{request_id[:8]}",
        )

        self._eins[request_id] = result
        return result

    async def get_ein_status(
        self, request_id: str
    ) -> EINResult:
        """Get mock EIN status."""
        if request_id not in self._eins:
            raise FormationError(f"EIN application not found: {request_id}")
        return self._eins[request_id]

    async def complete_ein(
        self, request_id: str, ein: str = "12-3456789"
    ) -> EINResult:
        """Complete a mock EIN (for testing)."""
        if request_id not in self._eins:
            raise FormationError(f"EIN application not found: {request_id}")

        result = self._eins[request_id]
        result.status = EINStatus.RECEIVED
        result.ein = ein
        result.confirmation_letter_url = f"https://mock.ignara.app/ein/{request_id}"
        result.updated_at = datetime.now(timezone.utc)

        return result

    def get_pricing(
        self,
        state: FormationState,
        business_type: BusinessType,
        options: Dict[str, Any]
    ) -> Dict[str, int]:
        """Get mock pricing."""
        return {
            "base": 5000,  # $50
            "total": 5000,
        }


class FormationService:
    """
    High-level service for business formation.

    Orchestrates provider interactions and maintains state.
    """

    def __init__(
        self,
        provider: Optional[FormationProvider] = None,
        default_provider: str = "zenbusiness",
    ):
        self.default_provider = default_provider

        if provider:
            self.provider = provider
        else:
            # Select provider based on environment
            provider_name = os.getenv("FORMATION_PROVIDER", default_provider)
            self.provider = self._create_provider(provider_name)

    def _create_provider(self, name: str) -> FormationProvider:
        """Create provider by name."""
        providers = {
            "stripe_atlas": StripeAtlasProvider,
            "zenbusiness": ZenBusinessProvider,
            "mock": MockFormationProvider,
        }

        if name not in providers:
            raise FormationError(f"Unknown provider: {name}")

        return providers[name]()

    async def form_llc(
        self,
        request: FormationRequest,
    ) -> FormationResult:
        """Form an LLC using the configured provider."""
        logger.info(f"Starting LLC formation for {request.business_name}")
        return await self.provider.submit_formation(request)

    async def get_status(
        self,
        request_id: str,
    ) -> FormationResult:
        """Get formation status."""
        return await self.provider.get_formation_status(request_id)

    async def apply_for_ein(
        self,
        request: EINRequest,
    ) -> EINResult:
        """Apply for EIN."""
        logger.info(f"Starting EIN application for {request.business_name}")
        return await self.provider.submit_ein_application(request)

    async def get_ein_status(
        self,
        request_id: str,
    ) -> EINResult:
        """Get EIN status."""
        return await self.provider.get_ein_status(request_id)

    def estimate_cost(
        self,
        state: FormationState,
        business_type: BusinessType = BusinessType.LLC,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, int]:
        """Estimate formation costs."""
        return self.provider.get_pricing(
            state,
            business_type,
            options or {},
        )
