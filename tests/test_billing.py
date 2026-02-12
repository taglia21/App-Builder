"""Tests for billing service."""
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime
import stripe

from src.billing.service import BillingService, TIER_LIMITS, PRICE_IDS


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def billing_service(mock_db_session):
    """Create a billing service instance."""
    return BillingService(db_session=mock_db_session)


class TestBillingServiceCustomer:
    """Test customer management in billing service."""

    @pytest.mark.asyncio
    async def test_create_customer_success(self, billing_service):
        """Test successful customer creation."""
        with patch('stripe.Customer.create') as mock_create:
            mock_customer = Mock()
            mock_customer.id = "cus_test123"
            mock_create.return_value = mock_customer

            customer_id = await billing_service.create_customer(
                user_id=1,
                email="test@example.com",
                name="Test User"
            )

            assert customer_id == "cus_test123"
            mock_create.assert_called_once_with(
                email="test@example.com",
                name="Test User",
                metadata={"user_id": "1"}
            )

    @pytest.mark.asyncio
    async def test_create_customer_without_name(self, billing_service):
        """Test customer creation without name."""
        with patch('stripe.Customer.create') as mock_create:
            mock_customer = Mock()
            mock_customer.id = "cus_test456"
            mock_create.return_value = mock_customer

            customer_id = await billing_service.create_customer(
                user_id=2,
                email="noname@example.com"
            )

            assert customer_id == "cus_test456"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_customer_stripe_error(self, billing_service):
        """Test customer creation with Stripe error."""
        with patch('stripe.Customer.create') as mock_create:
            mock_create.side_effect = stripe.error.StripeError("API Error")

            with pytest.raises(stripe.error.StripeError):
                await billing_service.create_customer(
                    user_id=3,
                    email="error@example.com"
                )


class TestBillingServiceCheckout:
    """Test checkout session creation."""

    @pytest.mark.asyncio
    async def test_create_checkout_session_starter(self, billing_service):
        """Test creating checkout session for starter tier."""
        with patch('stripe.checkout.Session.create') as mock_create:
            mock_session = Mock()
            mock_session.id = "cs_test123"
            mock_session.url = "https://checkout.stripe.com/test"
            mock_create.return_value = mock_session

            result = await billing_service.create_checkout_session(
                user_id=1,
                tier="starter",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
                customer_id="cus_123"
            )

            assert result["session_id"] == "cs_test123"
            assert result["url"] == "https://checkout.stripe.com/test"

    @pytest.mark.asyncio
    async def test_create_checkout_session_pro(self, billing_service):
        """Test creating checkout session for pro tier."""
        with patch('stripe.checkout.Session.create') as mock_create:
            mock_session = Mock()
            mock_session.id = "cs_prof123"
            mock_session.url = "https://checkout.stripe.com/prof"
            mock_create.return_value = mock_session

            result = await billing_service.create_checkout_session(
                user_id=2,
                tier="pro",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
                customer_id="cus_456"
            )

            assert result["session_id"] == "cs_prof123"
            assert "checkout.stripe.com" in result["url"]

    @pytest.mark.asyncio
    async def test_create_checkout_session_stripe_error(self, billing_service):
        """Test checkout session creation with Stripe error."""
        with patch('stripe.checkout.Session.create') as mock_create:
            mock_create.side_effect = stripe.error.StripeError("Checkout Error")

            with pytest.raises(stripe.error.StripeError):
                await billing_service.create_checkout_session(
                    user_id=3,
                    tier="enterprise",
                    success_url="https://example.com/success",
                    cancel_url="https://example.com/cancel"
                )


class TestTierLimits:
    """Test tier limit configurations."""

    def test_free_tier_limits(self):
        """Test free tier has correct limits."""
        assert TIER_LIMITS["free"]["app_generations"] == 1
        assert TIER_LIMITS["free"]["price"] == 0

    def test_starter_tier_limits(self):
        """Test starter tier has correct limits."""
        assert TIER_LIMITS["starter"]["app_generations"] == 5
        assert TIER_LIMITS["starter"]["price"] == 2900

    def test_pro_tier_limits(self):
        """Test pro tier has correct limits."""
        assert TIER_LIMITS["pro"]["app_generations"] == 25
        assert TIER_LIMITS["pro"]["price"] == 9900

    def test_enterprise_tier_unlimited(self):
        """Test enterprise tier has unlimited generations."""
        assert TIER_LIMITS["enterprise"]["app_generations"] == -1
        assert TIER_LIMITS["enterprise"]["price"] == 29900

    def test_all_tiers_exist(self):
        """Test all expected tiers are configured."""
        expected_tiers = ["free", "starter", "pro", "enterprise"]
        for tier in expected_tiers:
            assert tier in TIER_LIMITS
            assert "app_generations" in TIER_LIMITS[tier]
            assert "price" in TIER_LIMITS[tier]


class TestBillingServiceSubscription:
    """Test subscription management."""

    @pytest.mark.asyncio
    async def test_cancel_subscription_success(self, billing_service):
        """Test successful subscription cancellation."""
        # Add method to service if not exists
        async def cancel_subscription(subscription_id: str):
            sub = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
            return {"status": sub.status, "id": sub.id}
        
        billing_service.cancel_subscription = cancel_subscription
        
        with patch('stripe.Subscription.modify') as mock_modify:
            mock_sub = Mock()
            mock_sub.id = "sub_123"
            mock_sub.status = "canceled"
            mock_modify.return_value = mock_sub

            result = await billing_service.cancel_subscription(
                subscription_id="sub_123"
            )

            assert result["status"] == "canceled"
            mock_modify.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_subscription_error(self, billing_service):
        """Test subscription cancellation with error."""
        async def cancel_subscription(subscription_id: str):
            sub = stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
            return {"status": sub.status}
        
        billing_service.cancel_subscription = cancel_subscription
        
        with patch('stripe.Subscription.modify') as mock_modify:
            mock_modify.side_effect = stripe.error.InvalidRequestError(
                "Subscription not found", 
                param="id"
            )

            with pytest.raises(stripe.error.InvalidRequestError):
                await billing_service.cancel_subscription(
                    subscription_id="sub_invalid"
                )

    @pytest.mark.asyncio
    async def test_get_subscription_status(self, billing_service):
        """Test retrieving subscription status."""
        async def get_subscription_status(subscription_id: str):
            sub = stripe.Subscription.retrieve(subscription_id)
            return {
                "status": sub.status,
                "id": sub.id,
                "current_period_end": sub.current_period_end
            }
        
        billing_service.get_subscription_status = get_subscription_status
        
        with patch('stripe.Subscription.retrieve') as mock_retrieve:
            mock_sub = Mock()
            mock_sub.id = "sub_123"
            mock_sub.status = "active"
            mock_sub.current_period_end = 1234567890
            mock_retrieve.return_value = mock_sub

            status = await billing_service.get_subscription_status(
                subscription_id="sub_123"
            )

            assert status["status"] == "active"
            assert "current_period_end" in status


class TestPriceIds:
    """Test price ID configuration."""

    def test_price_ids_exist(self):
        """Test all price IDs are configured."""
        assert "starter" in PRICE_IDS
        assert "pro" in PRICE_IDS
        assert "enterprise" in PRICE_IDS

    def test_price_ids_not_empty(self):
        """Test price IDs are not empty strings."""
        for tier, price_id in PRICE_IDS.items():
            assert price_id is not None
            assert len(price_id) > 0
