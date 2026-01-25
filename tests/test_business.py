"""
Tests for Business Formation Module

Tests for LLC formation, EIN application, banking, and domain registration.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

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
    FORMATION_PRICES,
    EXPEDITED_FEE,
)

from src.business.formation import (
    FormationProvider,
    FormationService,
    MockFormationProvider,
    FormationError,
)

from src.business.domain import (
    DomainProvider,
    DomainService,
    MockDomainProvider,
    DomainError,
)

from src.business.banking import (
    BankingProvider,
    BankingService,
    MockBankingProvider,
    BankingError,
)

from src.business.service import (
    BusinessFormationService,
    BusinessFormationStatus,
    create_business_service,
)


# ============================================================================
# Model Tests
# ============================================================================

class TestBusinessModels:
    """Test business formation models."""
    
    def test_business_type_enum(self):
        """Test BusinessType enum values."""
        assert BusinessType.LLC.value == "llc"
        assert BusinessType.CORPORATION.value == "corporation"
        assert BusinessType.S_CORP.value == "s_corp"
    
    def test_formation_state_enum(self):
        """Test FormationState enum values."""
        assert FormationState.DELAWARE.value == "DE"
        assert FormationState.WYOMING.value == "WY"
        assert FormationState.CALIFORNIA.value == "CA"
    
    def test_formation_status_enum(self):
        """Test FormationStatus enum values."""
        assert FormationStatus.PENDING.value == "pending"
        assert FormationStatus.COMPLETED.value == "completed"
        assert FormationStatus.FAILED.value == "failed"
    
    def test_formation_request_validation(self):
        """Test FormationRequest validation."""
        request = FormationRequest(
            business_name="Test LLC",
            business_type=BusinessType.LLC,
            state=FormationState.DELAWARE,
            owner_name="John Doe",
            owner_email="john@example.com",
            street_address="123 Main St",
            city="Dover",
            state_address="DE",
            zip_code="19901",
            user_id="user-123",
        )
        
        assert request.business_name == "Test LLC"
        assert request.business_type == BusinessType.LLC
        assert request.state == FormationState.DELAWARE
        assert request.registered_agent is True  # Default
        assert request.expedited is False  # Default
    
    def test_formation_request_min_length(self):
        """Test FormationRequest field validation."""
        with pytest.raises(ValueError):
            FormationRequest(
                business_name="",  # Too short
                owner_name="John",
                owner_email="john@example.com",
                street_address="123 Main St",
                city="Dover",
                state_address="DE",
                zip_code="19901",
                user_id="user-123",
            )
    
    def test_formation_result_model(self):
        """Test FormationResult model."""
        result = FormationResult(
            request_id="req-123",
            status=FormationStatus.SUBMITTED,
            business_name="Test LLC",
            business_type=BusinessType.LLC,
            state=FormationState.DELAWARE,
            provider="test",
        )
        
        assert result.request_id == "req-123"
        assert result.status == FormationStatus.SUBMITTED
        assert result.ein is None
        assert result.created_at is not None
    
    def test_ein_request_model(self):
        """Test EINRequest model."""
        request = EINRequest(
            business_name="Test LLC",
            business_type=BusinessType.LLC,
            state=FormationState.DELAWARE,
            responsible_party_name="John Doe",
            street_address="123 Main St",
            city="Dover",
            state_address="DE",
            zip_code="19901",
            user_id="user-123",
        )
        
        assert request.business_name == "Test LLC"
        assert request.principal_activity == "Software development"  # Default
    
    def test_banking_request_model(self):
        """Test BankingRequest model."""
        request = BankingRequest(
            business_name="Test LLC",
            ein="12-3456789",
            business_type=BusinessType.LLC,
            state=FormationState.DELAWARE,
            formation_date=datetime.utcnow(),
            owner_name="John Doe",
            owner_email="john@example.com",
            owner_phone="+1-555-123-4567",
            street_address="123 Main St",
            city="Dover",
            state_address="DE",
            zip_code="19901",
            user_id="user-123",
        )
        
        assert request.account_type == BankAccountType.CHECKING  # Default
    
    def test_domain_request_model(self):
        """Test DomainRequest model."""
        request = DomainRequest(
            domain_name="testllc.com",
            registrant_name="John Doe",
            registrant_email="john@example.com",
            street_address="123 Main St",
            city="Dover",
            state="DE",
            zip_code="19901",
            user_id="user-123",
        )
        
        assert request.privacy_protection is True  # Default
        assert request.auto_renew is True  # Default
        assert request.years == 1  # Default
    
    def test_domain_request_years_validation(self):
        """Test DomainRequest years validation."""
        with pytest.raises(ValueError):
            DomainRequest(
                domain_name="test.com",
                registrant_name="John",
                registrant_email="john@example.com",
                street_address="123 Main",
                city="City",
                state="ST",
                zip_code="12345",
                user_id="user-123",
                years=15,  # Max is 10
            )
    
    def test_formation_prices_constant(self):
        """Test formation pricing constants."""
        de_llc = FORMATION_PRICES[FormationState.DELAWARE][BusinessType.LLC]
        assert de_llc == 8900  # $89
        
        wy_llc = FORMATION_PRICES[FormationState.WYOMING][BusinessType.LLC]
        assert wy_llc == 10200  # $102


# ============================================================================
# Mock Formation Provider Tests
# ============================================================================

class TestMockFormationProvider:
    """Test MockFormationProvider."""
    
    @pytest.fixture
    def provider(self):
        """Create mock formation provider."""
        return MockFormationProvider()
    
    @pytest.fixture
    def formation_request(self):
        """Create sample formation request."""
        return FormationRequest(
            business_name="Test Startup LLC",
            business_type=BusinessType.LLC,
            state=FormationState.DELAWARE,
            owner_name="Jane Doe",
            owner_email="jane@example.com",
            street_address="456 Tech Ave",
            city="Wilmington",
            state_address="DE",
            zip_code="19801",
            user_id="user-456",
        )
    
    @pytest.mark.asyncio
    async def test_submit_formation(self, provider, formation_request):
        """Test submitting LLC formation."""
        result = await provider.submit_formation(formation_request)
        
        assert result.status == FormationStatus.SUBMITTED
        assert result.business_name == "Test Startup LLC"
        assert result.provider == "mock"
        assert result.request_id is not None
    
    @pytest.mark.asyncio
    async def test_get_formation_status(self, provider, formation_request):
        """Test getting formation status."""
        # Submit first
        submit_result = await provider.submit_formation(formation_request)
        
        # Then check status
        status_result = await provider.get_formation_status(submit_result.request_id)
        
        assert status_result.request_id == submit_result.request_id
        assert status_result.status == FormationStatus.SUBMITTED
    
    @pytest.mark.asyncio
    async def test_formation_not_found(self, provider):
        """Test error when formation not found."""
        with pytest.raises(FormationError):
            await provider.get_formation_status("nonexistent-id")
    
    @pytest.mark.asyncio
    async def test_complete_formation(self, provider, formation_request):
        """Test completing a formation."""
        submit_result = await provider.submit_formation(formation_request)
        
        # Complete the formation
        complete_result = await provider.complete_formation(
            submit_result.request_id,
            ein="98-7654321"
        )
        
        assert complete_result.status == FormationStatus.COMPLETED
        assert complete_result.ein == "98-7654321"
        assert complete_result.certificate_url is not None
    
    @pytest.mark.asyncio
    async def test_submit_ein_application(self, provider):
        """Test EIN application submission."""
        request = EINRequest(
            business_name="Test LLC",
            business_type=BusinessType.LLC,
            state=FormationState.DELAWARE,
            responsible_party_name="John Doe",
            street_address="123 Main St",
            city="Dover",
            state_address="DE",
            zip_code="19901",
            user_id="user-123",
        )
        
        result = await provider.submit_ein_application(request)
        
        assert result.status == EINStatus.SUBMITTED
        assert result.business_name == "Test LLC"
        assert result.provider == "mock"
    
    @pytest.mark.asyncio
    async def test_complete_ein(self, provider):
        """Test completing EIN application."""
        request = EINRequest(
            business_name="Test LLC",
            business_type=BusinessType.LLC,
            state=FormationState.DELAWARE,
            responsible_party_name="John Doe",
            street_address="123 Main St",
            city="Dover",
            state_address="DE",
            zip_code="19901",
            user_id="user-123",
        )
        
        submit_result = await provider.submit_ein_application(request)
        complete_result = await provider.complete_ein(
            submit_result.request_id,
            ein="12-3456789"
        )
        
        assert complete_result.status == EINStatus.RECEIVED
        assert complete_result.ein == "12-3456789"
    
    def test_get_pricing(self, provider):
        """Test getting mock pricing."""
        pricing = provider.get_pricing(
            FormationState.DELAWARE,
            BusinessType.LLC,
            {}
        )
        
        assert "base" in pricing
        assert "total" in pricing
        assert pricing["total"] == 5000  # $50 mock price


# ============================================================================
# Formation Service Tests
# ============================================================================

class TestFormationService:
    """Test FormationService."""
    
    @pytest.fixture
    def service(self):
        """Create formation service with mock provider."""
        return FormationService(provider=MockFormationProvider())
    
    @pytest.fixture
    def formation_request(self):
        """Create sample formation request."""
        return FormationRequest(
            business_name="Service Test LLC",
            business_type=BusinessType.LLC,
            state=FormationState.WYOMING,
            owner_name="Test User",
            owner_email="test@example.com",
            street_address="789 Service Rd",
            city="Cheyenne",
            state_address="WY",
            zip_code="82001",
            user_id="user-789",
        )
    
    @pytest.mark.asyncio
    async def test_form_llc(self, service, formation_request):
        """Test forming LLC through service."""
        result = await service.form_llc(formation_request)
        
        assert result.status == FormationStatus.SUBMITTED
        assert result.business_name == "Service Test LLC"
    
    @pytest.mark.asyncio
    async def test_get_status(self, service, formation_request):
        """Test getting status through service."""
        submit_result = await service.form_llc(formation_request)
        status_result = await service.get_status(submit_result.request_id)
        
        assert status_result.request_id == submit_result.request_id
    
    def test_estimate_cost(self, service):
        """Test cost estimation."""
        cost = service.estimate_cost(
            FormationState.DELAWARE,
            BusinessType.LLC,
            {}
        )
        
        assert "total" in cost


# ============================================================================
# Mock Domain Provider Tests
# ============================================================================

class TestMockDomainProvider:
    """Test MockDomainProvider."""
    
    @pytest.fixture
    def provider(self):
        """Create mock domain provider."""
        return MockDomainProvider()
    
    @pytest.fixture
    def domain_request(self):
        """Create sample domain request."""
        return DomainRequest(
            domain_name="myawesomestartup.com",
            registrant_name="John Doe",
            registrant_email="john@example.com",
            street_address="123 Main St",
            city="Dover",
            state="DE",
            zip_code="19901",
            user_id="user-123",
            years=2,
        )
    
    @pytest.mark.asyncio
    async def test_check_availability_available(self, provider):
        """Test checking available domain."""
        result = await provider.check_availability("available-domain.com")
        
        assert result.status == DomainStatus.AVAILABLE
        assert result.domain_name == "available-domain.com"
    
    @pytest.mark.asyncio
    async def test_check_availability_unavailable(self, provider):
        """Test checking unavailable domain."""
        result = await provider.check_availability("google.com")
        
        assert result.status == DomainStatus.UNAVAILABLE
    
    @pytest.mark.asyncio
    async def test_register_domain(self, provider, domain_request):
        """Test registering a domain."""
        result = await provider.register_domain(domain_request)
        
        assert result.status == DomainStatus.REGISTERED
        assert result.domain_name == "myawesomestartup.com"
        assert result.auto_renew is True
        assert result.privacy_protection is True
        assert result.expiry_date is not None
    
    @pytest.mark.asyncio
    async def test_register_unavailable_domain(self, provider):
        """Test registering an unavailable domain."""
        request = DomainRequest(
            domain_name="google.com",
            registrant_name="John Doe",
            registrant_email="john@example.com",
            street_address="123 Main St",
            city="Dover",
            state="DE",
            zip_code="19901",
            user_id="user-123",
        )
        
        result = await provider.register_domain(request)
        assert result.status == DomainStatus.UNAVAILABLE
    
    @pytest.mark.asyncio
    async def test_get_domain_status(self, provider, domain_request):
        """Test getting domain status."""
        # Register first
        await provider.register_domain(domain_request)
        
        # Check status
        result = await provider.get_domain_status("myawesomestartup.com")
        assert result.status == DomainStatus.REGISTERED
    
    @pytest.mark.asyncio
    async def test_update_nameservers(self, provider, domain_request):
        """Test updating nameservers."""
        await provider.register_domain(domain_request)
        
        new_ns = ["ns1.vercel-dns.com", "ns2.vercel-dns.com"]
        result = await provider.update_nameservers("myawesomestartup.com", new_ns)
        
        assert result.nameservers == new_ns
    
    def test_get_pricing(self, provider):
        """Test getting domain pricing."""
        pricing = provider.get_pricing("test.com", 2)
        
        assert "base" in pricing
        assert "years" in pricing
        assert pricing["years"] == 2
        assert pricing["total"] == 999 * 2


# ============================================================================
# Domain Service Tests
# ============================================================================

class TestDomainService:
    """Test DomainService."""
    
    @pytest.fixture
    def service(self):
        """Create domain service with mock provider."""
        return DomainService(provider=MockDomainProvider())
    
    @pytest.mark.asyncio
    async def test_check_domain(self, service):
        """Test checking domain availability."""
        result = await service.check_domain("available.io")
        assert result.status == DomainStatus.AVAILABLE
    
    @pytest.mark.asyncio
    async def test_register_domain(self, service):
        """Test registering domain through service."""
        request = DomainRequest(
            domain_name="newstartup.io",
            registrant_name="Jane Doe",
            registrant_email="jane@example.com",
            street_address="456 Tech Ave",
            city="San Francisco",
            state="CA",
            zip_code="94105",
            user_id="user-456",
        )
        
        result = await service.register_domain(request)
        assert result.status == DomainStatus.REGISTERED
    
    @pytest.mark.asyncio
    async def test_suggest_domains(self, service):
        """Test domain suggestions."""
        suggestions = await service.suggest_domains("coolstartup")
        
        assert len(suggestions) > 0
        for suggestion in suggestions:
            assert suggestion.status == DomainStatus.AVAILABLE
            assert "coolstartup" in suggestion.domain_name


# ============================================================================
# Mock Banking Provider Tests
# ============================================================================

class TestMockBankingProvider:
    """Test MockBankingProvider."""
    
    @pytest.fixture
    def provider(self):
        """Create mock banking provider."""
        return MockBankingProvider()
    
    @pytest.fixture
    def banking_request(self):
        """Create sample banking request."""
        return BankingRequest(
            business_name="Test LLC",
            ein="12-3456789",
            business_type=BusinessType.LLC,
            state=FormationState.DELAWARE,
            formation_date=datetime.utcnow() - timedelta(days=7),
            owner_name="John Doe",
            owner_email="john@example.com",
            owner_phone="+1-555-123-4567",
            street_address="123 Main St",
            city="Dover",
            state_address="DE",
            zip_code="19901",
            user_id="user-123",
        )
    
    @pytest.mark.asyncio
    async def test_submit_application(self, provider, banking_request):
        """Test submitting bank application."""
        result = await provider.submit_application(banking_request)
        
        assert result.status == BankingStatus.APPLICATION_PENDING
        assert result.bank_name == "Mock Bank"
        assert result.provider == "mock"
    
    @pytest.mark.asyncio
    async def test_get_application_status(self, provider, banking_request):
        """Test getting application status."""
        submit_result = await provider.submit_application(banking_request)
        status_result = await provider.get_application_status(submit_result.request_id)
        
        assert status_result.request_id == submit_result.request_id
        assert status_result.status == BankingStatus.APPLICATION_PENDING
    
    @pytest.mark.asyncio
    async def test_approve_application(self, provider, banking_request):
        """Test approving bank application."""
        submit_result = await provider.submit_application(banking_request)
        approved_result = await provider.approve_application(submit_result.request_id)
        
        assert approved_result.status == BankingStatus.ACTIVE
        assert approved_result.account_number is not None
        assert approved_result.routing_number is not None
    
    @pytest.mark.asyncio
    async def test_application_not_found(self, provider):
        """Test error when application not found."""
        with pytest.raises(BankingError):
            await provider.get_application_status("nonexistent-id")


# ============================================================================
# Banking Service Tests
# ============================================================================

class TestBankingService:
    """Test BankingService."""
    
    @pytest.fixture
    def service(self):
        """Create banking service with mock provider."""
        return BankingService(provider=MockBankingProvider())
    
    @pytest.fixture
    def banking_request(self):
        """Create sample banking request."""
        return BankingRequest(
            business_name="Service Test LLC",
            ein="98-7654321",
            business_type=BusinessType.LLC,
            state=FormationState.WYOMING,
            formation_date=datetime.utcnow(),
            owner_name="Test User",
            owner_email="test@example.com",
            owner_phone="+1-555-987-6543",
            street_address="789 Bank St",
            city="Cheyenne",
            state_address="WY",
            zip_code="82001",
            user_id="user-789",
        )
    
    @pytest.mark.asyncio
    async def test_apply_for_account(self, service, banking_request):
        """Test applying for account through service."""
        result = await service.apply_for_account(banking_request)
        
        assert result.status == BankingStatus.APPLICATION_PENDING


# ============================================================================
# Business Formation Status Tests
# ============================================================================

class TestBusinessFormationStatus:
    """Test BusinessFormationStatus model."""
    
    def test_default_status(self):
        """Test default status values."""
        status = BusinessFormationStatus(user_id="user-123")
        
        assert status.formation_status == FormationStatus.PENDING
        assert status.ein_status == EINStatus.NOT_STARTED
        assert status.banking_status == BankingStatus.NOT_STARTED
        assert status.domain_status == DomainStatus.PENDING
    
    def test_is_complete_false(self):
        """Test incomplete status."""
        status = BusinessFormationStatus(user_id="user-123")
        assert status.is_complete is False
    
    def test_is_complete_true(self):
        """Test complete status."""
        status = BusinessFormationStatus(
            user_id="user-123",
            formation_status=FormationStatus.COMPLETED,
            ein_status=EINStatus.RECEIVED,
            banking_status=BankingStatus.ACTIVE,
            domain_status=DomainStatus.REGISTERED,
        )
        assert status.is_complete is True
    
    def test_completion_percentage_zero(self):
        """Test zero completion percentage."""
        status = BusinessFormationStatus(user_id="user-123")
        assert status.completion_percentage == 0
    
    def test_completion_percentage_partial(self):
        """Test partial completion percentage."""
        status = BusinessFormationStatus(
            user_id="user-123",
            formation_status=FormationStatus.COMPLETED,
            ein_status=EINStatus.RECEIVED,
        )
        assert status.completion_percentage == 55  # 30 + 25
    
    def test_completion_percentage_full(self):
        """Test full completion percentage."""
        status = BusinessFormationStatus(
            user_id="user-123",
            formation_status=FormationStatus.COMPLETED,
            ein_status=EINStatus.RECEIVED,
            banking_status=BankingStatus.ACTIVE,
            domain_status=DomainStatus.REGISTERED,
        )
        assert status.completion_percentage == 100
    
    def test_to_dict(self):
        """Test status to dict conversion."""
        status = BusinessFormationStatus(
            user_id="user-123",
            business_name="Test LLC",
            domain_name="test.com",
        )
        
        data = status.to_dict()
        
        assert data["user_id"] == "user-123"
        assert data["formation"]["business_name"] == "Test LLC"
        assert data["domain"]["domain_name"] == "test.com"


# ============================================================================
# Business Formation Service Tests
# ============================================================================

class TestBusinessFormationService:
    """Test BusinessFormationService."""
    
    @pytest.fixture
    def service(self):
        """Create service with mock providers."""
        return BusinessFormationService(use_mocks=True)
    
    @pytest.fixture
    def formation_request(self):
        """Create sample formation request."""
        return FormationRequest(
            business_name="Full Flow LLC",
            business_type=BusinessType.LLC,
            state=FormationState.DELAWARE,
            owner_name="Full Flow User",
            owner_email="flow@example.com",
            street_address="100 Flow St",
            city="Wilmington",
            state_address="DE",
            zip_code="19801",
            user_id="user-flow",
            project_id="project-123",
        )
    
    @pytest.mark.asyncio
    async def test_start_formation(self, service, formation_request):
        """Test starting formation process."""
        status = await service.start_formation(formation_request)
        
        assert status.user_id == "user-flow"
        assert status.business_name == "Full Flow LLC"
        assert status.formation_status == FormationStatus.SUBMITTED
        assert status.formation_id is not None
    
    @pytest.mark.asyncio
    async def test_check_domain_availability(self, service):
        """Test checking domain through unified service."""
        result = await service.check_domain_availability("available-test.com")
        assert result.status == DomainStatus.AVAILABLE
    
    @pytest.mark.asyncio
    async def test_suggest_domains(self, service):
        """Test domain suggestions through unified service."""
        suggestions = await service.suggest_domains("mycompany")
        assert len(suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_register_domain(self, service):
        """Test domain registration through unified service."""
        request = DomainRequest(
            domain_name="fullflow.io",
            registrant_name="Full Flow User",
            registrant_email="flow@example.com",
            street_address="100 Flow St",
            city="Wilmington",
            state="DE",
            zip_code="19801",
            user_id="user-flow",
            project_id="project-123",
        )
        
        status = await service.register_domain(request)
        
        assert status.domain_status == DomainStatus.REGISTERED
        assert status.domain_name == "fullflow.io"
    
    @pytest.mark.asyncio
    async def test_get_status(self, service, formation_request):
        """Test getting overall status."""
        await service.start_formation(formation_request)
        
        status = await service.get_status("user-flow", "project-123")
        
        assert status.user_id == "user-flow"
        assert status.business_name == "Full Flow LLC"
    
    def test_estimate_costs(self, service):
        """Test cost estimation."""
        costs = service.estimate_costs(
            state=FormationState.DELAWARE,
            business_type=BusinessType.LLC,
            domain_name="test.com",
        )
        
        assert "formation" in costs
        assert "domain" in costs
        assert "total" in costs
        assert "formatted_total" in costs
    
    def test_estimate_costs_no_domain(self, service):
        """Test cost estimation without domain."""
        costs = service.estimate_costs(
            state=FormationState.WYOMING,
        )
        
        assert costs["domain"]["total"] == 0


# ============================================================================
# Factory Function Tests
# ============================================================================

class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_business_service(self):
        """Test creating business service."""
        service = create_business_service(use_mocks=True)
        
        assert isinstance(service, BusinessFormationService)
        assert isinstance(service.formation.provider, MockFormationProvider)
        assert isinstance(service.domain.provider, MockDomainProvider)
        assert isinstance(service.banking.provider, MockBankingProvider)


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling."""
    
    def test_formation_error(self):
        """Test FormationError exception."""
        error = FormationError("Test error")
        assert str(error) == "Test error"
    
    def test_domain_error(self):
        """Test DomainError exception."""
        error = DomainError("Domain error")
        assert str(error) == "Domain error"
    
    def test_banking_error(self):
        """Test BankingError exception."""
        error = BankingError("Banking error")
        assert str(error) == "Banking error"
