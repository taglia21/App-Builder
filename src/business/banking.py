"""
Business Banking Providers

Pluggable providers for business bank account setup.
Supports Mercury, Relay, and mock providers.
"""

import os
import uuid
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx

from src.business.models import (
    BusinessType,
    FormationState,
    BankingStatus,
    BankAccountType,
    BankingRequest,
    BankingResult,
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
    Mercury Bank API integration.
    
    Mercury is popular for startups and tech companies.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        sandbox: bool = True,
    ):
        self.api_key = api_key or os.getenv("MERCURY_API_KEY")
        self.sandbox = sandbox
        self.base_url = (
            "https://api.mercury.com/api/v1" 
            if not sandbox 
            else "https://api.sandbox.mercury.com/api/v1"
        )
    
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
        """Submit Mercury bank account application."""
        if not self.api_key:
            raise BankingError("Mercury API key not configured")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/onboarding/applications",
                    headers=self._get_headers(),
                    json={
                        "companyName": request.business_name,
                        "ein": request.ein,
                        "entityType": request.business_type.value,
                        "stateOfFormation": request.state.value,
                        "formationDate": request.formation_date.isoformat(),
                        "primaryContact": {
                            "name": request.owner_name,
                            "email": request.owner_email,
                            "phone": request.owner_phone,
                        },
                        "address": {
                            "street": request.street_address,
                            "city": request.city,
                            "state": request.state_address,
                            "postalCode": request.zip_code,
                            "country": "US",
                        },
                        "expectedMonthlyRevenue": request.estimated_monthly_revenue or 0,
                        "accountType": request.account_type.value,
                    },
                    timeout=60.0,
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    return BankingResult(
                        request_id=data.get("applicationId", str(uuid.uuid4())),
                        status=BankingStatus.APPLICATION_PENDING,
                        bank_name="Mercury",
                        account_type=request.account_type,
                        provider=self.name,
                        provider_reference=data.get("applicationId"),
                        dashboard_url=data.get("onboardingUrl"),
                        message="Application submitted. Complete verification at the provided URL.",
                        verification_steps=["Email verification", "Identity verification", "Business documentation"],
                    )
                else:
                    raise BankingError(f"Mercury API error: {response.text}")
                    
        except httpx.RequestError as e:
            raise BankingError(f"Request failed: {e}")
    
    async def get_application_status(
        self, request_id: str
    ) -> BankingResult:
        """Get Mercury application status."""
        if not self.api_key:
            raise BankingError("Mercury API key not configured")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/onboarding/applications/{request_id}",
                    headers=self._get_headers(),
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    status_map = {
                        "pending": BankingStatus.APPLICATION_PENDING,
                        "verification_required": BankingStatus.VERIFICATION_REQUIRED,
                        "approved": BankingStatus.APPROVED,
                        "active": BankingStatus.ACTIVE,
                        "rejected": BankingStatus.REJECTED,
                    }
                    
                    return BankingResult(
                        request_id=request_id,
                        status=status_map.get(data.get("status"), BankingStatus.APPLICATION_PENDING),
                        bank_name="Mercury",
                        account_type=BankAccountType(data.get("accountType", "checking")),
                        account_number=data.get("accountNumber"),  # Will be masked
                        routing_number=data.get("routingNumber"),
                        dashboard_url=data.get("dashboardUrl"),
                        provider=self.name,
                        provider_reference=request_id,
                        message=data.get("statusMessage"),
                        verification_steps=data.get("pendingSteps", []),
                    )
                else:
                    raise BankingError(f"Failed to get application status: {response.text}")
                    
        except httpx.RequestError as e:
            raise BankingError(f"Request failed: {e}")
    
    async def get_account_info(
        self, account_id: str
    ) -> BankingResult:
        """Get Mercury account information."""
        if not self.api_key:
            raise BankingError("Mercury API key not configured")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/accounts/{account_id}",
                    headers=self._get_headers(),
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return BankingResult(
                        request_id=account_id,
                        status=BankingStatus.ACTIVE,
                        bank_name="Mercury",
                        account_type=BankAccountType(data.get("type", "checking")),
                        account_number=data.get("accountNumber"),
                        routing_number=data.get("routingNumber"),
                        dashboard_url="https://app.mercury.com",
                        provider=self.name,
                        provider_reference=account_id,
                    )
                else:
                    raise BankingError(f"Failed to get account info: {response.text}")
                    
        except httpx.RequestError as e:
            raise BankingError(f"Request failed: {e}")


class RelayProvider(BankingProvider):
    """
    Relay Bank API integration.
    
    Relay is another popular choice for startups.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        sandbox: bool = True,
    ):
        self.api_key = api_key or os.getenv("RELAY_API_KEY")
        self.sandbox = sandbox
        self.base_url = (
            "https://api.relay.com/v1"
            if not sandbox
            else "https://sandbox.api.relay.com/v1"
        )
    
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
        """Submit Relay bank account application."""
        if not self.api_key:
            raise BankingError("Relay API key not configured")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/applications",
                    headers=self._get_headers(),
                    json={
                        "business": {
                            "name": request.business_name,
                            "ein": request.ein,
                            "type": request.business_type.value,
                            "stateOfFormation": request.state.value,
                            "formationDate": request.formation_date.isoformat(),
                            "address": {
                                "line1": request.street_address,
                                "city": request.city,
                                "state": request.state_address,
                                "postalCode": request.zip_code,
                            },
                        },
                        "owner": {
                            "name": request.owner_name,
                            "email": request.owner_email,
                            "phone": request.owner_phone,
                        },
                        "accountType": request.account_type.value,
                    },
                    timeout=60.0,
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    return BankingResult(
                        request_id=data.get("id", str(uuid.uuid4())),
                        status=BankingStatus.APPLICATION_PENDING,
                        bank_name="Relay",
                        account_type=request.account_type,
                        provider=self.name,
                        provider_reference=data.get("id"),
                        dashboard_url=data.get("signupUrl"),
                        message="Application submitted. Complete verification steps.",
                        verification_steps=["Identity verification", "Business verification"],
                    )
                else:
                    raise BankingError(f"Relay API error: {response.text}")
                    
        except httpx.RequestError as e:
            raise BankingError(f"Request failed: {e}")
    
    async def get_application_status(
        self, request_id: str
    ) -> BankingResult:
        """Get Relay application status."""
        if not self.api_key:
            raise BankingError("Relay API key not configured")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/applications/{request_id}",
                    headers=self._get_headers(),
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    status_map = {
                        "pending": BankingStatus.APPLICATION_PENDING,
                        "needs_info": BankingStatus.VERIFICATION_REQUIRED,
                        "approved": BankingStatus.APPROVED,
                        "active": BankingStatus.ACTIVE,
                        "declined": BankingStatus.REJECTED,
                    }
                    
                    return BankingResult(
                        request_id=request_id,
                        status=status_map.get(data.get("status"), BankingStatus.APPLICATION_PENDING),
                        bank_name="Relay",
                        account_type=BankAccountType(data.get("accountType", "checking")),
                        account_number=data.get("accountNumber"),
                        routing_number=data.get("routingNumber"),
                        dashboard_url=data.get("dashboardUrl", "https://app.relay.com"),
                        provider=self.name,
                        provider_reference=request_id,
                    )
                else:
                    raise BankingError(f"Failed to get application status: {response.text}")
                    
        except httpx.RequestError as e:
            raise BankingError(f"Request failed: {e}")
    
    async def get_account_info(
        self, account_id: str
    ) -> BankingResult:
        """Get Relay account information."""
        if not self.api_key:
            raise BankingError("Relay API key not configured")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/accounts/{account_id}",
                    headers=self._get_headers(),
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return BankingResult(
                        request_id=account_id,
                        status=BankingStatus.ACTIVE,
                        bank_name="Relay",
                        account_type=BankAccountType(data.get("type", "checking")),
                        account_number=data.get("accountNumber"),
                        routing_number=data.get("routingNumber"),
                        dashboard_url="https://app.relay.com",
                        provider=self.name,
                        provider_reference=account_id,
                    )
                else:
                    raise BankingError(f"Failed to get account info: {response.text}")
                    
        except httpx.RequestError as e:
            raise BankingError(f"Request failed: {e}")


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
        result.updated_at = datetime.utcnow()
        
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
