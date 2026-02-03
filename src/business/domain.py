"""
Domain Registration Providers

Pluggable providers for domain registration.
Supports Namecheap, GoDaddy, and mock providers.
"""

import logging
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import httpx

from src.business.models import (
    DomainRequest,
    DomainResult,
    DomainStatus,
)

logger = logging.getLogger(__name__)


class DomainError(Exception):
    """Base exception for domain errors."""
    pass


class DomainProvider(ABC):
    """Abstract base class for domain providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @abstractmethod
    async def check_availability(
        self, domain_name: str
    ) -> DomainResult:
        """Check if domain is available."""
        pass

    @abstractmethod
    async def register_domain(
        self, request: DomainRequest
    ) -> DomainResult:
        """Register a domain."""
        pass

    @abstractmethod
    async def get_domain_status(
        self, domain_name: str
    ) -> DomainResult:
        """Get domain status."""
        pass

    @abstractmethod
    async def update_nameservers(
        self, domain_name: str,
        nameservers: List[str]
    ) -> DomainResult:
        """Update domain nameservers."""
        pass

    @abstractmethod
    def get_pricing(
        self, domain_name: str,
        years: int = 1
    ) -> Dict[str, int]:
        """Get domain pricing."""
        pass


class NamecheapProvider(DomainProvider):
    """Namecheap API integration."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_user: Optional[str] = None,
        username: Optional[str] = None,
        client_ip: Optional[str] = None,
        sandbox: bool = True,
    ):
        self.api_key = api_key or os.getenv("NAMECHEAP_API_KEY")
        self.api_user = api_user or os.getenv("NAMECHEAP_API_USER")
        self.username = username or os.getenv("NAMECHEAP_USERNAME")
        self.client_ip = client_ip or os.getenv("NAMECHEAP_CLIENT_IP", "127.0.0.1")
        self.sandbox = sandbox

        self.base_url = (
            "https://api.sandbox.namecheap.com/xml.response"
            if sandbox
            else "https://api.namecheap.com/xml.response"
        )

        # TLD pricing (in cents)
        self.tld_prices = {
            ".com": 1299,  # $12.99
            ".net": 1399,  # $13.99
            ".org": 1299,  # $12.99
            ".io": 5999,   # $59.99
            ".co": 2999,   # $29.99
            ".app": 1999,  # $19.99
            ".dev": 1499,  # $14.99
            ".ai": 12999,  # $129.99
        }

    @property
    def name(self) -> str:
        return "namecheap"

    def _get_params(self) -> Dict[str, str]:
        """Get base API parameters."""
        return {
            "ApiUser": self.api_user or "",
            "ApiKey": self.api_key or "",
            "UserName": self.username or "",
            "ClientIp": self.client_ip,
        }

    async def check_availability(
        self, domain_name: str
    ) -> DomainResult:
        """Check domain availability via Namecheap API."""
        if not self.api_key:
            raise DomainError("Namecheap API key not configured")

        try:
            params = self._get_params()
            params.update({
                "Command": "namecheap.domains.check",
                "DomainList": domain_name,
            })

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url,
                    params=params,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    # Parse XML response (simplified)
                    is_available = "Available=\"true\"" in response.text

                    return DomainResult(
                        request_id=str(uuid.uuid4()),
                        status=DomainStatus.AVAILABLE if is_available else DomainStatus.UNAVAILABLE,
                        domain_name=domain_name,
                        registrar=self.name,
                        provider=self.name,
                        message="Domain is available" if is_available else "Domain is not available",
                    )
                else:
                    raise DomainError(f"Namecheap API error: {response.text}")

        except httpx.RequestError as e:
            raise DomainError(f"Request failed: {e}")

    async def register_domain(
        self, request: DomainRequest
    ) -> DomainResult:
        """Register domain via Namecheap."""
        if not self.api_key:
            raise DomainError("Namecheap API key not configured")

        # First check availability
        availability = await self.check_availability(request.domain_name)
        if availability.status != DomainStatus.AVAILABLE:
            return availability

        try:
            params = self._get_params()
            params.update({
                "Command": "namecheap.domains.create",
                "DomainName": request.domain_name,
                "Years": str(request.years),
                # Registrant info
                "RegistrantFirstName": request.registrant_name.split()[0],
                "RegistrantLastName": " ".join(request.registrant_name.split()[1:]) or request.registrant_name,
                "RegistrantAddress1": request.street_address,
                "RegistrantCity": request.city,
                "RegistrantStateProvince": request.state,
                "RegistrantPostalCode": request.zip_code,
                "RegistrantCountry": request.country,
                "RegistrantPhone": request.registrant_phone or "+1.0000000000",
                "RegistrantEmailAddress": request.registrant_email,
                # Copy for other contacts
                "TechFirstName": request.registrant_name.split()[0],
                "TechLastName": " ".join(request.registrant_name.split()[1:]) or request.registrant_name,
                "TechAddress1": request.street_address,
                "TechCity": request.city,
                "TechStateProvince": request.state,
                "TechPostalCode": request.zip_code,
                "TechCountry": request.country,
                "TechPhone": request.registrant_phone or "+1.0000000000",
                "TechEmailAddress": request.registrant_email,
                # Options
                "AddFreeWhoisguard": "yes" if request.privacy_protection else "no",
                "WGEnabled": "yes" if request.privacy_protection else "no",
            })

            # Add nameservers if provided
            if request.nameservers:
                for i, ns in enumerate(request.nameservers[:5], 1):
                    params[f"Nameserver{i}"] = ns

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    data=params,
                    timeout=60.0,
                )

                if response.status_code == 200 and "Status=\"OK\"" in response.text:
                    return DomainResult(
                        request_id=str(uuid.uuid4()),
                        status=DomainStatus.REGISTERED,
                        domain_name=request.domain_name,
                        registrar=self.name,
                        registered_date=datetime.now(timezone.utc),
                        expiry_date=datetime.now(timezone.utc) + timedelta(days=365 * request.years),
                        auto_renew=request.auto_renew,
                        privacy_protection=request.privacy_protection,
                        nameservers=request.nameservers,
                        provider=self.name,
                        provider_reference=request.domain_name,
                        price_paid=self.get_pricing(request.domain_name, request.years)["total"],
                        message="Domain registered successfully",
                    )
                else:
                    raise DomainError(f"Registration failed: {response.text}")

        except httpx.RequestError as e:
            raise DomainError(f"Request failed: {e}")

    async def get_domain_status(
        self, domain_name: str
    ) -> DomainResult:
        """Get domain status from Namecheap."""
        if not self.api_key:
            raise DomainError("Namecheap API key not configured")

        try:
            params = self._get_params()
            params.update({
                "Command": "namecheap.domains.getInfo",
                "DomainName": domain_name,
            })

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url,
                    params=params,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    # Parse response (simplified)
                    is_expired = "IsExpired=\"true\"" in response.text

                    return DomainResult(
                        request_id=str(uuid.uuid4()),
                        status=DomainStatus.EXPIRED if is_expired else DomainStatus.REGISTERED,
                        domain_name=domain_name,
                        registrar=self.name,
                        provider=self.name,
                        management_url=f"https://ap.www.namecheap.com/domains/domaincontrolpanel/{domain_name}",
                    )
                else:
                    raise DomainError(f"Failed to get domain info: {response.text}")

        except httpx.RequestError as e:
            raise DomainError(f"Request failed: {e}")

    async def update_nameservers(
        self, domain_name: str,
        nameservers: List[str]
    ) -> DomainResult:
        """Update nameservers via Namecheap."""
        if not self.api_key:
            raise DomainError("Namecheap API key not configured")

        # Extract SLD and TLD
        parts = domain_name.split(".")
        sld = parts[0]
        tld = ".".join(parts[1:])

        try:
            params = self._get_params()
            params.update({
                "Command": "namecheap.domains.dns.setCustom",
                "SLD": sld,
                "TLD": tld,
                "Nameservers": ",".join(nameservers),
            })

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    data=params,
                    timeout=30.0,
                )

                if response.status_code == 200 and "Status=\"OK\"" in response.text:
                    return DomainResult(
                        request_id=str(uuid.uuid4()),
                        status=DomainStatus.REGISTERED,
                        domain_name=domain_name,
                        registrar=self.name,
                        nameservers=nameservers,
                        provider=self.name,
                        message="Nameservers updated successfully",
                    )
                else:
                    raise DomainError(f"Failed to update nameservers: {response.text}")

        except httpx.RequestError as e:
            raise DomainError(f"Request failed: {e}")

    def get_pricing(
        self, domain_name: str,
        years: int = 1
    ) -> Dict[str, int]:
        """Get domain pricing."""
        # Get TLD
        tld = "." + ".".join(domain_name.split(".")[1:])
        base_price = self.tld_prices.get(tld, 1499)  # Default to $14.99

        return {
            "base": base_price,
            "years": years,
            "privacy": 0,  # Usually included
            "total": base_price * years,
        }


class GoDaddyProvider(DomainProvider):
    """GoDaddy API integration."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        sandbox: bool = True,
    ):
        self.api_key = api_key or os.getenv("GODADDY_API_KEY")
        self.api_secret = api_secret or os.getenv("GODADDY_API_SECRET")
        self.sandbox = sandbox

        self.base_url = (
            "https://api.ote-godaddy.com/v1"
            if sandbox
            else "https://api.godaddy.com/v1"
        )

        self.tld_prices = {
            ".com": 1799,  # $17.99
            ".net": 1499,
            ".org": 1299,
            ".io": 6999,
            ".co": 3499,
        }

    @property
    def name(self) -> str:
        return "godaddy"

    def _get_headers(self) -> Dict[str, str]:
        """Get API headers."""
        return {
            "Authorization": f"sso-key {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json",
        }

    async def check_availability(
        self, domain_name: str
    ) -> DomainResult:
        """Check domain availability via GoDaddy API."""
        if not self.api_key:
            raise DomainError("GoDaddy API key not configured")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/domains/available",
                    headers=self._get_headers(),
                    params={"domain": domain_name},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    is_available = data.get("available", False)

                    return DomainResult(
                        request_id=str(uuid.uuid4()),
                        status=DomainStatus.AVAILABLE if is_available else DomainStatus.UNAVAILABLE,
                        domain_name=domain_name,
                        registrar=self.name,
                        provider=self.name,
                        message="Domain is available" if is_available else "Domain is not available",
                    )
                else:
                    raise DomainError(f"GoDaddy API error: {response.text}")

        except httpx.RequestError as e:
            raise DomainError(f"Request failed: {e}")

    async def register_domain(
        self, request: DomainRequest
    ) -> DomainResult:
        """Register domain via GoDaddy."""
        if not self.api_key:
            raise DomainError("GoDaddy API key not configured")

        try:
            contact = {
                "nameFirst": request.registrant_name.split()[0],
                "nameLast": " ".join(request.registrant_name.split()[1:]) or request.registrant_name,
                "email": request.registrant_email,
                "phone": request.registrant_phone or "+1.0000000000",
                "addressMailing": {
                    "address1": request.street_address,
                    "city": request.city,
                    "state": request.state,
                    "postalCode": request.zip_code,
                    "country": request.country,
                },
            }

            body = {
                "domain": request.domain_name,
                "consent": {
                    "agreedAt": datetime.now(timezone.utc).isoformat() + "Z",
                    "agreedBy": request.registrant_email,
                    "agreementKeys": ["DNRA"],
                },
                "contactAdmin": contact,
                "contactBilling": contact,
                "contactRegistrant": contact,
                "contactTech": contact,
                "period": request.years,
                "privacy": request.privacy_protection,
                "renewAuto": request.auto_renew,
            }

            if request.nameservers:
                body["nameServers"] = request.nameservers

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/domains/purchase",
                    headers=self._get_headers(),
                    json=body,
                    timeout=60.0,
                )

                if response.status_code in (200, 201):
                    return DomainResult(
                        request_id=str(uuid.uuid4()),
                        status=DomainStatus.REGISTERED,
                        domain_name=request.domain_name,
                        registrar=self.name,
                        registered_date=datetime.now(timezone.utc),
                        expiry_date=datetime.now(timezone.utc) + timedelta(days=365 * request.years),
                        auto_renew=request.auto_renew,
                        privacy_protection=request.privacy_protection,
                        nameservers=request.nameservers,
                        provider=self.name,
                        price_paid=self.get_pricing(request.domain_name, request.years)["total"],
                        message="Domain registered successfully",
                    )
                else:
                    raise DomainError(f"Registration failed: {response.text}")

        except httpx.RequestError as e:
            raise DomainError(f"Request failed: {e}")

    async def get_domain_status(
        self, domain_name: str
    ) -> DomainResult:
        """Get domain status from GoDaddy."""
        if not self.api_key:
            raise DomainError("GoDaddy API key not configured")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/domains/{domain_name}",
                    headers=self._get_headers(),
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()

                    status = DomainStatus.REGISTERED
                    if data.get("status") == "EXPIRED":
                        status = DomainStatus.EXPIRED

                    return DomainResult(
                        request_id=str(uuid.uuid4()),
                        status=status,
                        domain_name=domain_name,
                        registrar=self.name,
                        expiry_date=datetime.fromisoformat(data["expires"].replace("Z", "+00:00")) if data.get("expires") else None,
                        nameservers=data.get("nameServers", []),
                        auto_renew=data.get("renewAuto", False),
                        privacy_protection=data.get("privacy", False),
                        provider=self.name,
                        management_url=f"https://dcc.godaddy.com/manage/{domain_name}",
                    )
                else:
                    raise DomainError(f"Failed to get domain info: {response.text}")

        except httpx.RequestError as e:
            raise DomainError(f"Request failed: {e}")

    async def update_nameservers(
        self, domain_name: str,
        nameservers: List[str]
    ) -> DomainResult:
        """Update nameservers via GoDaddy."""
        if not self.api_key:
            raise DomainError("GoDaddy API key not configured")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/domains/{domain_name}",
                    headers=self._get_headers(),
                    json={"nameServers": nameservers},
                    timeout=30.0,
                )

                if response.status_code in (200, 204):
                    return DomainResult(
                        request_id=str(uuid.uuid4()),
                        status=DomainStatus.REGISTERED,
                        domain_name=domain_name,
                        registrar=self.name,
                        nameservers=nameservers,
                        provider=self.name,
                        message="Nameservers updated successfully",
                    )
                else:
                    raise DomainError(f"Failed to update nameservers: {response.text}")

        except httpx.RequestError as e:
            raise DomainError(f"Request failed: {e}")

    def get_pricing(
        self, domain_name: str,
        years: int = 1
    ) -> Dict[str, int]:
        """Get domain pricing."""
        tld = "." + ".".join(domain_name.split(".")[1:])
        base_price = self.tld_prices.get(tld, 1799)

        return {
            "base": base_price,
            "years": years,
            "privacy": 999,  # $9.99/year for GoDaddy
            "total": (base_price + 999) * years,
        }


class MockDomainProvider(DomainProvider):
    """Mock provider for testing."""

    def __init__(self):
        self._domains: Dict[str, DomainResult] = {}
        self._unavailable: set = {"taken.com", "google.com", "facebook.com"}

    @property
    def name(self) -> str:
        return "mock"

    async def check_availability(
        self, domain_name: str
    ) -> DomainResult:
        """Check mock domain availability."""
        is_available = (
            domain_name not in self._unavailable
            and domain_name not in self._domains
        )

        return DomainResult(
            request_id=str(uuid.uuid4()),
            status=DomainStatus.AVAILABLE if is_available else DomainStatus.UNAVAILABLE,
            domain_name=domain_name,
            registrar=self.name,
            provider=self.name,
            message="Domain is available" if is_available else "Domain is not available",
        )

    async def register_domain(
        self, request: DomainRequest
    ) -> DomainResult:
        """Register mock domain."""
        availability = await self.check_availability(request.domain_name)
        if availability.status != DomainStatus.AVAILABLE:
            return availability

        result = DomainResult(
            request_id=str(uuid.uuid4()),
            status=DomainStatus.REGISTERED,
            domain_name=request.domain_name,
            registrar=self.name,
            registered_date=datetime.now(timezone.utc),
            expiry_date=datetime.now(timezone.utc) + timedelta(days=365 * request.years),
            auto_renew=request.auto_renew,
            privacy_protection=request.privacy_protection,
            nameservers=request.nameservers,
            provider=self.name,
            provider_reference=f"MOCK-{request.domain_name}",
            price_paid=self.get_pricing(request.domain_name, request.years)["total"],
            message="Domain registered successfully",
        )

        self._domains[request.domain_name] = result
        return result

    async def get_domain_status(
        self, domain_name: str
    ) -> DomainResult:
        """Get mock domain status."""
        if domain_name in self._domains:
            return self._domains[domain_name]

        return DomainResult(
            request_id=str(uuid.uuid4()),
            status=DomainStatus.UNAVAILABLE,
            domain_name=domain_name,
            registrar=self.name,
            provider=self.name,
            message="Domain not found in account",
        )

    async def update_nameservers(
        self, domain_name: str,
        nameservers: List[str]
    ) -> DomainResult:
        """Update mock nameservers."""
        if domain_name not in self._domains:
            raise DomainError(f"Domain not found: {domain_name}")

        result = self._domains[domain_name]
        result.nameservers = nameservers
        result.updated_at = datetime.now(timezone.utc)
        result.message = "Nameservers updated successfully"

        return result

    def get_pricing(
        self, domain_name: str,
        years: int = 1
    ) -> Dict[str, int]:
        """Get mock pricing."""
        return {
            "base": 999,  # $9.99
            "years": years,
            "privacy": 0,
            "total": 999 * years,
        }


class DomainService:
    """High-level service for domain management."""

    def __init__(
        self,
        provider: Optional[DomainProvider] = None,
        default_provider: str = "namecheap",
    ):
        self.default_provider = default_provider

        if provider:
            self.provider = provider
        else:
            provider_name = os.getenv("DOMAIN_PROVIDER", default_provider)
            self.provider = self._create_provider(provider_name)

    def _create_provider(self, name: str) -> DomainProvider:
        """Create provider by name."""
        providers = {
            "namecheap": NamecheapProvider,
            "godaddy": GoDaddyProvider,
            "mock": MockDomainProvider,
        }

        if name not in providers:
            raise DomainError(f"Unknown provider: {name}")

        return providers[name]()

    async def check_domain(
        self, domain_name: str
    ) -> DomainResult:
        """Check if domain is available."""
        logger.info(f"Checking availability for {domain_name}")
        return await self.provider.check_availability(domain_name)

    async def register_domain(
        self, request: DomainRequest
    ) -> DomainResult:
        """Register a domain."""
        logger.info(f"Registering domain {request.domain_name}")
        return await self.provider.register_domain(request)

    async def get_status(
        self, domain_name: str
    ) -> DomainResult:
        """Get domain status."""
        return await self.provider.get_domain_status(domain_name)

    async def update_dns(
        self, domain_name: str,
        nameservers: List[str]
    ) -> DomainResult:
        """Update domain nameservers."""
        logger.info(f"Updating nameservers for {domain_name}")
        return await self.provider.update_nameservers(domain_name, nameservers)

    def estimate_cost(
        self, domain_name: str,
        years: int = 1
    ) -> Dict[str, int]:
        """Estimate domain registration cost."""
        return self.provider.get_pricing(domain_name, years)

    async def suggest_domains(
        self, keyword: str,
        tlds: Optional[List[str]] = None
    ) -> List[DomainResult]:
        """Suggest available domains based on keyword."""
        tlds = tlds or [".com", ".io", ".co", ".app", ".dev"]
        suggestions = []

        for tld in tlds:
            domain = f"{keyword}{tld}"
            result = await self.check_domain(domain)
            if result.status == DomainStatus.AVAILABLE:
                result.renewal_price = self.provider.get_pricing(domain)["total"]
                suggestions.append(result)

        return suggestions
