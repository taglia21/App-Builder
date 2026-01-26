"""
LLC/Business Formation Providers

Pluggable providers for business formation services.
Supports Stripe Atlas, ZenBusiness, and mock providers for testing.
"""

import os
import uuid
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import httpx

from src.business.models import (
    BusinessType,
    FormationState,
    FormationStatus,
    FormationRequest,
    FormationResult,
    EINStatus,
    EINRequest,
    EINResult,
    FORMATION_PRICES,
    EXPEDITED_FEE,
    REGISTERED_AGENT_ANNUAL,
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
    Stripe Atlas integration for business formation.
    
    Note: Stripe Atlas requires manual approval and has specific
    requirements. This provider uses their API for status tracking.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        sandbox: bool = True,
    ):
        self.api_key = api_key or os.getenv("STRIPE_ATLAS_API_KEY")
        self.webhook_secret = webhook_secret or os.getenv("STRIPE_ATLAS_WEBHOOK_SECRET")
        self.sandbox = sandbox
        self.base_url = "https://api.stripe.com/v1/atlas" if not sandbox else "https://api.stripe.com/v1/atlas"
        
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
        Submit to Stripe Atlas.
        
        Note: In production, this would create an Atlas application
        and return a link for the user to complete.
        """
        if not self.api_key:
            raise FormationError("Stripe Atlas API key not configured")
        
        request_id = str(uuid.uuid4())
        
        # In reality, Stripe Atlas requires manual application
        # This simulates creating an application link
        logger.info(f"Creating Stripe Atlas application for {request.business_name}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/applications",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "company_name": request.business_name,
                        "type": request.business_type.value,
                        "state": request.state.value,
                        "owner": {
                            "name": request.owner_name,
                            "email": request.owner_email,
                        },
                        "metadata": {
                            "user_id": request.user_id,
                            "project_id": request.project_id,
                        },
                    },
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return FormationResult(
                        request_id=data.get("id", request_id),
                        status=FormationStatus.PENDING,
                        business_name=request.business_name,
                        business_type=request.business_type,
                        state=request.state,
                        provider=self.name,
                        provider_reference=data.get("application_url"),
                        message="Complete your Stripe Atlas application at the provided URL",
                        estimated_completion=datetime.utcnow() + timedelta(days=5),
                    )
                else:
                    raise FormationError(f"Stripe Atlas error: {response.text}")
                    
        except httpx.RequestError as e:
            logger.error(f"Stripe Atlas request failed: {e}")
            raise FormationError(f"Request failed: {e}")
    
    async def get_formation_status(
        self, request_id: str
    ) -> FormationResult:
        """Get Stripe Atlas application status."""
        if not self.api_key:
            raise FormationError("Stripe Atlas API key not configured")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/applications/{request_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Map Stripe Atlas status to our status
                    status_map = {
                        "pending": FormationStatus.PENDING,
                        "submitted": FormationStatus.SUBMITTED,
                        "in_review": FormationStatus.PROCESSING,
                        "approved": FormationStatus.APPROVED,
                        "rejected": FormationStatus.REJECTED,
                        "completed": FormationStatus.COMPLETED,
                    }
                    
                    return FormationResult(
                        request_id=request_id,
                        status=status_map.get(data.get("status"), FormationStatus.PENDING),
                        business_name=data.get("company_name", ""),
                        business_type=BusinessType(data.get("type", "llc")),
                        state=FormationState(data.get("state", "DE")),
                        ein=data.get("ein"),
                        formation_date=datetime.fromisoformat(data["formation_date"]) if data.get("formation_date") else None,
                        certificate_url=data.get("certificate_url"),
                        provider=self.name,
                        provider_reference=request_id,
                    )
                else:
                    raise FormationError(f"Failed to get status: {response.text}")
                    
        except httpx.RequestError as e:
            raise FormationError(f"Request failed: {e}")
    
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
        """Get EIN status from Atlas."""
        # Get formation status which includes EIN
        formation = await self.get_formation_status(request_id)
        
        return EINResult(
            request_id=request_id,
            status=EINStatus.RECEIVED if formation.ein else EINStatus.PENDING,
            ein=formation.ein,
            business_name=formation.business_name,
            provider=self.name,
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
    ZenBusiness integration for business formation.
    
    More flexible pricing than Stripe Atlas.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        sandbox: bool = True,
    ):
        self.api_key = api_key or os.getenv("ZENBUSINESS_API_KEY")
        self.sandbox = sandbox
        self.base_url = "https://api.zenbusiness.com/v1" if not sandbox else "https://sandbox.api.zenbusiness.com/v1"
    
    @property
    def name(self) -> str:
        return "zenbusiness"
    
    async def submit_formation(
        self, request: FormationRequest
    ) -> FormationResult:
        """Submit formation to ZenBusiness."""
        if not self.api_key:
            raise FormationError("ZenBusiness API key not configured")
        
        request_id = str(uuid.uuid4())
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/formations",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "company_name": request.business_name,
                        "entity_type": request.business_type.value,
                        "state": request.state.value,
                        "contact": {
                            "first_name": request.owner_name.split()[0],
                            "last_name": " ".join(request.owner_name.split()[1:]) or request.owner_name,
                            "email": request.owner_email,
                            "phone": request.owner_phone,
                        },
                        "address": {
                            "street": request.street_address,
                            "city": request.city,
                            "state": request.state_address,
                            "zip": request.zip_code,
                            "country": request.country,
                        },
                        "purpose": request.purpose,
                        "registered_agent": request.registered_agent,
                        "operating_agreement": request.operating_agreement,
                        "expedited": request.expedited,
                    },
                    timeout=30.0,
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    return FormationResult(
                        request_id=data.get("order_id", request_id),
                        status=FormationStatus.SUBMITTED,
                        business_name=request.business_name,
                        business_type=request.business_type,
                        state=request.state,
                        provider=self.name,
                        provider_reference=data.get("order_id"),
                        message="Formation submitted successfully",
                        estimated_completion=datetime.utcnow() + timedelta(days=3 if request.expedited else 7),
                    )
                else:
                    raise FormationError(f"ZenBusiness error: {response.text}")
                    
        except httpx.RequestError as e:
            logger.error(f"ZenBusiness request failed: {e}")
            raise FormationError(f"Request failed: {e}")
    
    async def get_formation_status(
        self, request_id: str
    ) -> FormationResult:
        """Get ZenBusiness formation status."""
        if not self.api_key:
            raise FormationError("ZenBusiness API key not configured")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/formations/{request_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    status_map = {
                        "pending": FormationStatus.PENDING,
                        "processing": FormationStatus.PROCESSING,
                        "filed": FormationStatus.APPROVED,
                        "completed": FormationStatus.COMPLETED,
                        "rejected": FormationStatus.REJECTED,
                    }
                    
                    return FormationResult(
                        request_id=request_id,
                        status=status_map.get(data.get("status"), FormationStatus.PENDING),
                        business_name=data.get("company_name", ""),
                        business_type=BusinessType(data.get("entity_type", "llc")),
                        state=FormationState(data.get("state", "DE")),
                        ein=data.get("ein"),
                        formation_date=datetime.fromisoformat(data["filed_date"]) if data.get("filed_date") else None,
                        certificate_url=data.get("documents", {}).get("certificate"),
                        operating_agreement_url=data.get("documents", {}).get("operating_agreement"),
                        provider=self.name,
                        provider_reference=request_id,
                    )
                else:
                    raise FormationError(f"Failed to get status: {response.text}")
                    
        except httpx.RequestError as e:
            raise FormationError(f"Request failed: {e}")
    
    async def submit_ein_application(
        self, request: EINRequest
    ) -> EINResult:
        """Submit EIN application through ZenBusiness."""
        if not self.api_key:
            raise FormationError("ZenBusiness API key not configured")
        
        request_id = str(uuid.uuid4())
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/ein",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "company_name": request.business_name,
                        "entity_type": request.business_type.value,
                        "state": request.state.value,
                        "responsible_party": {
                            "name": request.responsible_party_name,
                            "ssn_last4": request.responsible_party_ssn[-4:] if request.responsible_party_ssn else None,
                        },
                        "address": {
                            "street": request.street_address,
                            "city": request.city,
                            "state": request.state_address,
                            "zip": request.zip_code,
                        },
                        "principal_activity": request.principal_activity,
                        "expected_employees": request.expected_employees,
                    },
                    timeout=30.0,
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    return EINResult(
                        request_id=data.get("application_id", request_id),
                        status=EINStatus.SUBMITTED,
                        business_name=request.business_name,
                        message="EIN application submitted",
                        provider=self.name,
                        provider_reference=data.get("application_id"),
                    )
                else:
                    raise FormationError(f"EIN application failed: {response.text}")
                    
        except httpx.RequestError as e:
            raise FormationError(f"Request failed: {e}")
    
    async def get_ein_status(
        self, request_id: str
    ) -> EINResult:
        """Get EIN status from ZenBusiness."""
        if not self.api_key:
            raise FormationError("ZenBusiness API key not configured")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/ein/{request_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    status_map = {
                        "pending": EINStatus.PENDING,
                        "submitted": EINStatus.SUBMITTED,
                        "received": EINStatus.RECEIVED,
                        "failed": EINStatus.FAILED,
                    }
                    
                    return EINResult(
                        request_id=request_id,
                        status=status_map.get(data.get("status"), EINStatus.PENDING),
                        ein=data.get("ein"),
                        business_name=data.get("company_name", ""),
                        confirmation_letter_url=data.get("confirmation_letter_url"),
                        provider=self.name,
                        provider_reference=request_id,
                    )
                else:
                    raise FormationError(f"Failed to get EIN status: {response.text}")
                    
        except httpx.RequestError as e:
            raise FormationError(f"Request failed: {e}")
    
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
            estimated_completion=datetime.utcnow() + timedelta(days=3),
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
        result.formation_date = datetime.utcnow()
        result.certificate_url = f"https://mock.nexusai.dev/certs/{request_id}"
        result.updated_at = datetime.utcnow()
        
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
        result.confirmation_letter_url = f"https://mock.nexusai.dev/ein/{request_id}"
        result.updated_at = datetime.utcnow()
        
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
