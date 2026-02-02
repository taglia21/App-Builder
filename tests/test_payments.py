"""
Tests for Stripe payments module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import timezone, datetime, timedelta
import stripe

from src.payments.stripe_client import (
    StripeClient,
    StripeError,
    PaymentError,
    SubscriptionError,
    CustomerError,
    StripeCustomer,
    StripeSubscription,
    StripeInvoice,
    StripePaymentIntent,
)
from src.payments.subscription import (
    SubscriptionManager,
    SubscriptionTier,
    PricingPlan,
    UserSubscription,
    PRICING_PLANS,
)
from src.payments.webhooks import (
    WebhookProcessor,
    WebhookEvent,
    WebhookEventType,
    WebhookError,
    SubscriptionWebhookHandler,
)
from src.payments.credits import (
    CreditManager,
    CreditType,
    TransactionType,
    CreditTransaction,
    CreditBalance,
    InsufficientCreditsError,
    CREDIT_COSTS,
)


# ============== Stripe Client Tests ==============

class TestStripeClient:
    """Tests for StripeClient."""
    
    def test_init_with_api_key(self):
        """Test initialization with API key."""
        client = StripeClient(api_key="sk_test_123")
        assert client.api_key == "sk_test_123"
    
    def test_init_without_api_key(self):
        """Test initialization without API key."""
        with patch.dict('os.environ', {}, clear=True):
            client = StripeClient()
            assert client.api_key is None
    
    @patch('stripe.Customer.create')
    def test_create_customer(self, mock_create):
        """Test customer creation."""
        mock_customer = MagicMock()
        mock_customer.id = "cus_123"
        mock_customer.email = "test@example.com"
        mock_customer.name = "Test User"
        mock_customer.created = 1609459200  # 2021-01-01
        mock_customer.invoice_settings.default_payment_method = None
        mock_customer.metadata = {}
        mock_create.return_value = mock_customer
        
        client = StripeClient(api_key="sk_test_123")
        customer = client.create_customer(
            email="test@example.com",
            name="Test User",
            metadata={"user_id": "user_123"},
        )
        
        assert customer.id == "cus_123"
        assert customer.email == "test@example.com"
        assert customer.name == "Test User"
        mock_create.assert_called_once()
    
    @patch('stripe.Customer.retrieve')
    def test_get_customer(self, mock_retrieve):
        """Test getting customer."""
        mock_retrieve.return_value = Mock(
            id="cus_123",
            email="test@example.com",
            name="Test User",
            created=1609459200,
            invoice_settings=Mock(default_payment_method="pm_123"),
            metadata={"tier": "pro"},
        )
        
        client = StripeClient(api_key="sk_test_123")
        customer = client.get_customer("cus_123")
        
        assert customer.id == "cus_123"
        assert customer.default_payment_method == "pm_123"
    
    @patch('stripe.Customer.modify')
    def test_update_customer(self, mock_modify):
        """Test updating customer."""
        mock_customer = MagicMock()
        mock_customer.id = "cus_123"
        mock_customer.email = "new@example.com"
        mock_customer.name = "Updated Name"
        mock_customer.created = 1609459200
        mock_customer.invoice_settings.default_payment_method = None
        mock_customer.metadata = {}
        mock_modify.return_value = mock_customer
        
        client = StripeClient(api_key="sk_test_123")
        customer = client.update_customer(
            customer_id="cus_123",
            email="new@example.com",
            name="Updated Name",
        )
        
        assert customer.email == "new@example.com"
        assert customer.name == "Updated Name"
    
    @patch('stripe.Customer.delete')
    def test_delete_customer(self, mock_delete):
        """Test deleting customer."""
        mock_delete.return_value = Mock(deleted=True)
        
        client = StripeClient(api_key="sk_test_123")
        result = client.delete_customer("cus_123")
        
        assert result is True
    
    @patch('stripe.Subscription.create')
    def test_create_subscription(self, mock_create):
        """Test subscription creation."""
        mock_sub = MagicMock()
        mock_sub.id = "sub_123"
        mock_sub.customer = "cus_123"
        mock_sub.status = "active"
        mock_sub.current_period_start = 1609459200
        mock_sub.current_period_end = 1612137600
        mock_sub.cancel_at_period_end = False
        mock_sub.metadata = {}
        mock_sub.__getitem__ = lambda self, key: {"items": MagicMock(data=[MagicMock(price=MagicMock(id="price_123", product="prod_123"))])}[key]
        mock_create.return_value = mock_sub
        
        client = StripeClient(api_key="sk_test_123")
        subscription = client.create_subscription(
            customer_id="cus_123",
            price_id="price_123",
        )
        
        assert subscription.id == "sub_123"
        assert subscription.status == "active"
    
    @patch('stripe.Subscription.modify')
    @patch('stripe.Subscription.retrieve')
    def test_update_subscription(self, mock_retrieve, mock_modify):
        """Test subscription update."""
        mock_retrieve.return_value = {
            "items": {"data": [MagicMock(id="si_123")]}
        }
        
        # Create a proper mock with attribute access for item.price.id
        class MockPrice:
            id = "price_456"
            product = "prod_123"
        
        class MockItem:
            price = MockPrice()
        
        class MockSubscription:
            id = "sub_123"
            customer = "cus_123"
            status = "active"
            current_period_start = 1609459200
            current_period_end = 1612137600
            cancel_at_period_end = False
            metadata = {}
            
            def __getitem__(self, key):
                if key == "items":
                    # Return a dict-like object that supports ["data"][0]
                    return {"data": [MockItem()]}
                raise KeyError(key)
        
        mock_modify.return_value = MockSubscription()
        
        client = StripeClient(api_key="sk_test_123")
        subscription = client.update_subscription(
            subscription_id="sub_123",
            price_id="price_456",
        )
        
        assert subscription.price_id == "price_456"
    
    @patch('stripe.Subscription.delete')
    def test_cancel_subscription_immediately(self, mock_delete):
        """Test immediate subscription cancellation."""
        mock_sub = MagicMock()
        mock_sub.id = "sub_123"
        mock_sub.customer = "cus_123"
        mock_sub.status = "canceled"
        mock_sub.current_period_start = 1609459200
        mock_sub.current_period_end = 1612137600
        mock_sub.cancel_at_period_end = False
        mock_sub.metadata = {}
        mock_sub.__getitem__ = lambda self, key: {"items": MagicMock(data=[MagicMock(price=MagicMock(id="price_123", product="prod_123"))])}[key]
        mock_delete.return_value = mock_sub
        
        client = StripeClient(api_key="sk_test_123")
        subscription = client.cancel_subscription("sub_123", immediately=True)
        
        assert subscription.status == "canceled"
    
    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent(self, mock_create):
        """Test payment intent creation."""
        mock_create.return_value = Mock(
            id="pi_123",
            amount=2900,
            currency="usd",
            status="requires_payment_method",
            client_secret="pi_123_secret",
            customer=None,
            payment_method=None,
        )
        
        client = StripeClient(api_key="sk_test_123")
        intent = client.create_payment_intent(amount=2900, currency="usd")
        
        assert intent.id == "pi_123"
        assert intent.amount == 2900
        assert intent.client_secret == "pi_123_secret"
    
    @patch('stripe.checkout.Session.create')
    def test_create_checkout_session(self, mock_create):
        """Test checkout session creation."""
        mock_create.return_value = Mock(
            id="cs_123",
            url="https://checkout.stripe.com/...",
            customer=None,
            subscription=None,
        )
        
        client = StripeClient(api_key="sk_test_123")
        session = client.create_checkout_session(
            price_id="price_123",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )
        
        assert session["id"] == "cs_123"
        assert "url" in session


class TestStripeErrorHandling:
    """Tests for Stripe error handling."""
    
    def test_card_error_raises_payment_error(self):
        """Test that card errors become PaymentError."""
        client = StripeClient(api_key="sk_test_123")
        
        with patch('stripe.PaymentIntent.create') as mock_create:
            mock_create.side_effect = stripe.CardError(
                message="Card declined",
                param="card",
                code="card_declined",
            )
            
            with pytest.raises(PaymentError) as exc_info:
                client.create_payment_intent(amount=1000)
            
            assert "Card declined" in str(exc_info.value)
    
    def test_invalid_request_error_handling(self):
        """Test invalid request error handling."""
        client = StripeClient(api_key="sk_test_123")
        
        with patch('stripe.Customer.retrieve') as mock_retrieve:
            mock_retrieve.side_effect = stripe.InvalidRequestError(
                message="No such customer",
                param="customer",
            )
            
            with pytest.raises(CustomerError):
                client.get_customer("cus_invalid")


# ============== Subscription Manager Tests ==============

class TestSubscriptionTiers:
    """Tests for subscription tiers and plans."""
    
    def test_all_tiers_defined(self):
        """Test all subscription tiers are defined."""
        assert SubscriptionTier.FREE in PRICING_PLANS
        assert SubscriptionTier.PRO in PRICING_PLANS
        assert SubscriptionTier.ENTERPRISE in PRICING_PLANS
    
    def test_free_tier_pricing(self):
        """Test free tier has zero cost."""
        plan = PRICING_PLANS[SubscriptionTier.FREE]
        assert plan.price_monthly == 0
        assert plan.price_yearly == 0
    
    def test_pro_tier_pricing(self):
        """Test pro tier pricing."""
        plan = PRICING_PLANS[SubscriptionTier.PRO]
        assert plan.price_monthly == 2900  # $29
        assert plan.price_yearly == 29000  # $290
    
    def test_enterprise_tier_pricing(self):
        """Test enterprise tier pricing."""
        plan = PRICING_PLANS[SubscriptionTier.ENTERPRISE]
        assert plan.price_monthly == 9900  # $99
        assert plan.price_yearly == 99000  # $990
    
    def test_free_tier_limits(self):
        """Test free tier feature limits."""
        plan = PRICING_PLANS[SubscriptionTier.FREE]
        assert plan.apps_per_month == 1
        assert plan.priority_support is False
        assert plan.api_access is False
    
    def test_pro_tier_features(self):
        """Test pro tier features."""
        plan = PRICING_PLANS[SubscriptionTier.PRO]
        assert plan.apps_per_month == 5
        assert plan.priority_support is True
        assert plan.custom_domains is True
    
    def test_enterprise_unlimited(self):
        """Test enterprise has unlimited features."""
        plan = PRICING_PLANS[SubscriptionTier.ENTERPRISE]
        assert plan.apps_per_month == -1  # Unlimited
        assert plan.team_members == -1  # Unlimited
        assert plan.api_access is True
        assert plan.white_label is True


class TestUserSubscription:
    """Tests for UserSubscription dataclass."""
    
    def test_can_create_app_free_tier(self):
        """Test app creation limits for free tier."""
        sub = UserSubscription(
            user_id="user_123",
            tier=SubscriptionTier.FREE,
            apps_created_this_month=0,
        )
        
        assert sub.can_create_app is True
        
        sub.apps_created_this_month = 1
        assert sub.can_create_app is False
    
    def test_can_create_app_pro_tier(self):
        """Test app creation limits for pro tier."""
        sub = UserSubscription(
            user_id="user_123",
            tier=SubscriptionTier.PRO,
            apps_created_this_month=4,
        )
        
        assert sub.can_create_app is True
        
        sub.apps_created_this_month = 5
        assert sub.can_create_app is False
    
    def test_can_create_app_enterprise_unlimited(self):
        """Test enterprise has unlimited app creation."""
        sub = UserSubscription(
            user_id="user_123",
            tier=SubscriptionTier.ENTERPRISE,
            apps_created_this_month=100,
        )
        
        assert sub.can_create_app is True
    
    def test_apps_remaining_calculation(self):
        """Test remaining apps calculation."""
        sub = UserSubscription(
            user_id="user_123",
            tier=SubscriptionTier.PRO,
            apps_created_this_month=2,
        )
        
        assert sub.apps_remaining == 3
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        sub = UserSubscription(
            user_id="user_123",
            tier=SubscriptionTier.PRO,
            status="active",
        )
        
        data = sub.to_dict()
        assert data["user_id"] == "user_123"
        assert data["tier"] == "pro"
        assert data["status"] == "active"
        assert "plan" in data


class TestSubscriptionManager:
    """Tests for SubscriptionManager."""
    
    def test_get_plan(self):
        """Test getting a pricing plan."""
        manager = SubscriptionManager()
        plan = manager.get_plan(SubscriptionTier.PRO)
        
        assert plan.tier == SubscriptionTier.PRO
        assert plan.price_monthly == 2900
    
    def test_get_all_plans(self):
        """Test getting all plans."""
        manager = SubscriptionManager()
        plans = manager.get_all_plans()
        
        assert len(plans) == 3
    
    def test_create_free_subscription(self):
        """Test creating free subscription (no Stripe)."""
        manager = SubscriptionManager()
        
        sub = manager.create_subscription(
            user_id="user_123",
            email="test@example.com",
            tier=SubscriptionTier.FREE,
        )
        
        assert sub.tier == SubscriptionTier.FREE
        assert sub.status == "active"
        assert sub.stripe_customer_id is None
    
    def test_check_feature_access(self):
        """Test feature access checking."""
        manager = SubscriptionManager()
        
        free_sub = UserSubscription(
            user_id="user_123",
            tier=SubscriptionTier.FREE,
        )
        
        pro_sub = UserSubscription(
            user_id="user_456",
            tier=SubscriptionTier.PRO,
        )
        
        assert manager.check_feature_access(free_sub, "priority_support") is False
        assert manager.check_feature_access(pro_sub, "priority_support") is True
        assert manager.check_feature_access(free_sub, "api_access") is False


# ============== Webhook Tests ==============

class TestWebhookEvent:
    """Tests for WebhookEvent parsing."""
    
    def test_webhook_event_creation(self):
        """Test creating WebhookEvent directly."""
        event = WebhookEvent(
            id="evt_123",
            type="customer.subscription.created",
            created=datetime.fromtimestamp(1609459200),
            data={"id": "sub_123", "customer": "cus_123", "status": "active"},
            livemode=False,
            customer_id="cus_123",
            subscription_id="sub_123",
        )
        
        assert event.id == "evt_123"
        assert event.type == "customer.subscription.created"
        assert event.customer_id == "cus_123"
        assert event.subscription_id == "sub_123"
        assert event.livemode is False


class TestWebhookProcessor:
    """Tests for WebhookProcessor."""
    
    def test_register_handler(self):
        """Test registering a handler."""
        processor = WebhookProcessor()
        
        def my_handler(event):
            return "handled"
        
        processor.register_handler("test.event", my_handler)
        assert "test.event" in processor._handlers
    
    def test_on_decorator(self):
        """Test @on decorator."""
        processor = WebhookProcessor()
        
        @processor.on("checkout.session.completed")
        def handle_checkout(event):
            return "checkout handled"
        
        assert "checkout.session.completed" in processor._handlers
    
    def test_process_event_with_handler(self):
        """Test processing event with registered handler."""
        processor = WebhookProcessor()
        
        handled_events = []
        
        @processor.on("test.event")
        def handle_test(event):
            handled_events.append(event)
            return {"success": True}
        
        event = WebhookEvent(
            id="evt_123",
            type="test.event",
            created=datetime.now(timezone.utc),
            data={"key": "value"},
            livemode=False,
        )
        
        result = processor.process(event)
        
        assert result["status"] == "success"
        assert len(handled_events) == 1
    
    def test_process_event_no_handler(self):
        """Test processing event without handler."""
        processor = WebhookProcessor()
        
        event = WebhookEvent(
            id="evt_123",
            type="unknown.event",
            created=datetime.now(timezone.utc),
            data={},
            livemode=False,
        )
        
        result = processor.process(event)
        
        assert result["status"] == "ignored"
    
    def test_process_event_handler_error(self):
        """Test processing event when handler raises error."""
        processor = WebhookProcessor()
        
        @processor.on("error.event")
        def handle_error(event):
            raise ValueError("Handler failed")
        
        event = WebhookEvent(
            id="evt_123",
            type="error.event",
            created=datetime.now(timezone.utc),
            data={},
            livemode=False,
        )
        
        result = processor.process(event)
        
        assert result["status"] == "partial_failure"
        assert len(result["errors"]) == 1


class TestSubscriptionWebhookHandler:
    """Tests for default subscription webhook handlers."""
    
    def test_handlers_registered(self):
        """Test that all handlers are registered."""
        processor = WebhookProcessor()
        handler = SubscriptionWebhookHandler(processor)
        
        expected_events = [
            WebhookEventType.CHECKOUT_COMPLETED.value,
            WebhookEventType.SUBSCRIPTION_CREATED.value,
            WebhookEventType.SUBSCRIPTION_UPDATED.value,
            WebhookEventType.SUBSCRIPTION_DELETED.value,
            WebhookEventType.INVOICE_PAID.value,
            WebhookEventType.INVOICE_PAYMENT_FAILED.value,
            WebhookEventType.SUBSCRIPTION_TRIAL_ENDING.value,
        ]
        
        for event_type in expected_events:
            assert event_type in processor._handlers
    
    def test_handle_checkout_completed(self):
        """Test checkout completed handler."""
        processor = WebhookProcessor()
        handler = SubscriptionWebhookHandler(processor)
        
        event = WebhookEvent(
            id="evt_123",
            type=WebhookEventType.CHECKOUT_COMPLETED.value,
            created=datetime.now(timezone.utc),
            data={
                "customer": "cus_123",
                "subscription": "sub_123",
                "customer_email": "test@example.com",
            },
            livemode=False,
        )
        
        result = handler.handle_checkout_completed(event)
        
        assert result["action"] == "provision_access"
        assert result["customer_id"] == "cus_123"
    
    def test_handle_subscription_deleted(self):
        """Test subscription deletion handler."""
        processor = WebhookProcessor()
        handler = SubscriptionWebhookHandler(processor)
        
        event = WebhookEvent(
            id="evt_123",
            type=WebhookEventType.SUBSCRIPTION_DELETED.value,
            created=datetime.now(timezone.utc),
            data={
                "id": "sub_123",
                "customer": "cus_123",
            },
            livemode=False,
        )
        
        result = handler.handle_subscription_deleted(event)
        
        assert result["action"] == "subscription_cancelled"


# ============== Credit Manager Tests ==============

class TestCreditBalance:
    """Tests for CreditBalance."""
    
    def test_available_credits(self):
        """Test available credits calculation."""
        balance = CreditBalance(
            user_id="user_123",
            credit_type=CreditType.APP_GENERATION,
            balance=10,
            reserved=3,
            expires_at=None,
            last_updated=datetime.now(timezone.utc),
        )
        
        assert balance.available == 7
    
    def test_expired_credits(self):
        """Test credit expiration check."""
        balance = CreditBalance(
            user_id="user_123",
            credit_type=CreditType.APP_GENERATION,
            balance=10,
            reserved=0,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            last_updated=datetime.now(timezone.utc),
        )
        
        assert balance.is_expired is True
    
    def test_non_expired_credits(self):
        """Test non-expired credits."""
        balance = CreditBalance(
            user_id="user_123",
            credit_type=CreditType.APP_GENERATION,
            balance=10,
            reserved=0,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            last_updated=datetime.now(timezone.utc),
        )
        
        assert balance.is_expired is False


class TestCreditManager:
    """Tests for CreditManager."""
    
    def test_get_balance_new_user(self):
        """Test getting balance for new user."""
        manager = CreditManager()
        balance = manager.get_balance("new_user", CreditType.APP_GENERATION)
        
        assert balance.balance == 0
        assert balance.user_id == "new_user"
    
    def test_add_credits(self):
        """Test adding credits."""
        manager = CreditManager()
        
        txn = manager.add_credits(
            user_id="user_123",
            credit_type=CreditType.APP_GENERATION,
            amount=10,
            transaction_type=TransactionType.SUBSCRIPTION_GRANT,
            description="Monthly credit grant",
        )
        
        assert txn.amount == 10
        assert txn.transaction_type == TransactionType.SUBSCRIPTION_GRANT
        
        balance = manager.get_balance("user_123", CreditType.APP_GENERATION)
        assert balance.balance == 10
    
    def test_use_credits(self):
        """Test using credits."""
        manager = CreditManager()
        
        # Add credits first
        manager.add_credits(
            user_id="user_123",
            credit_type=CreditType.APP_GENERATION,
            amount=10,
            transaction_type=TransactionType.SUBSCRIPTION_GRANT,
            description="Grant",
        )
        
        # Use credits
        txn = manager.use_credits(
            user_id="user_123",
            credit_type=CreditType.APP_GENERATION,
            amount=3,
            description="Generated app",
        )
        
        assert txn.amount == -3
        
        balance = manager.get_balance("user_123", CreditType.APP_GENERATION)
        assert balance.balance == 7
    
    def test_use_credits_insufficient(self):
        """Test using more credits than available."""
        manager = CreditManager()
        
        manager.add_credits(
            user_id="user_123",
            credit_type=CreditType.APP_GENERATION,
            amount=5,
            transaction_type=TransactionType.SUBSCRIPTION_GRANT,
            description="Grant",
        )
        
        with pytest.raises(InsufficientCreditsError) as exc_info:
            manager.use_credits(
                user_id="user_123",
                credit_type=CreditType.APP_GENERATION,
                amount=10,
                description="Too much",
            )
        
        assert exc_info.value.required == 10
        assert exc_info.value.available == 5
    
    def test_reserve_and_commit(self):
        """Test credit reservation workflow."""
        manager = CreditManager()
        
        manager.add_credits(
            user_id="user_123",
            credit_type=CreditType.APP_GENERATION,
            amount=10,
            transaction_type=TransactionType.SUBSCRIPTION_GRANT,
            description="Grant",
        )
        
        # Reserve
        manager.reserve_credits("user_123", CreditType.APP_GENERATION, 5)
        
        balance = manager.get_balance("user_123", CreditType.APP_GENERATION)
        assert balance.balance == 10
        assert balance.reserved == 5
        assert balance.available == 5
        
        # Commit
        txn = manager.commit_reservation(
            user_id="user_123",
            credit_type=CreditType.APP_GENERATION,
            amount=5,
            description="Committed reservation",
        )
        
        balance = manager.get_balance("user_123", CreditType.APP_GENERATION)
        assert balance.balance == 5
        assert balance.reserved == 0
    
    def test_release_reservation(self):
        """Test releasing a reservation."""
        manager = CreditManager()
        
        manager.add_credits(
            user_id="user_123",
            credit_type=CreditType.APP_GENERATION,
            amount=10,
            transaction_type=TransactionType.SUBSCRIPTION_GRANT,
            description="Grant",
        )
        
        manager.reserve_credits("user_123", CreditType.APP_GENERATION, 5)
        manager.release_reservation("user_123", CreditType.APP_GENERATION, 5)
        
        balance = manager.get_balance("user_123", CreditType.APP_GENERATION)
        assert balance.reserved == 0
        assert balance.available == 10
    
    def test_refund_credits(self):
        """Test refunding credits."""
        manager = CreditManager()
        
        # Use credits
        manager.add_credits(
            user_id="user_123",
            credit_type=CreditType.APP_GENERATION,
            amount=10,
            transaction_type=TransactionType.SUBSCRIPTION_GRANT,
            description="Grant",
        )
        
        manager.use_credits(
            user_id="user_123",
            credit_type=CreditType.APP_GENERATION,
            amount=5,
            description="Used",
        )
        
        # Refund
        txn = manager.refund_credits(
            user_id="user_123",
            credit_type=CreditType.APP_GENERATION,
            amount=3,
            description="Refund for failed generation",
        )
        
        assert txn.transaction_type == TransactionType.REFUND
        
        balance = manager.get_balance("user_123", CreditType.APP_GENERATION)
        assert balance.balance == 8  # 10 - 5 + 3
    
    def test_get_transactions(self):
        """Test getting transaction history."""
        manager = CreditManager()
        
        manager.add_credits(
            user_id="user_123",
            credit_type=CreditType.APP_GENERATION,
            amount=10,
            transaction_type=TransactionType.SUBSCRIPTION_GRANT,
            description="Grant 1",
        )
        
        manager.add_credits(
            user_id="user_123",
            credit_type=CreditType.APP_GENERATION,
            amount=5,
            transaction_type=TransactionType.BONUS,
            description="Bonus",
        )
        
        transactions = manager.get_transactions("user_123")
        
        assert len(transactions) == 2
        assert transactions[0].description == "Bonus"  # Most recent first
    
    def test_grant_subscription_credits(self):
        """Test granting subscription credits."""
        manager = CreditManager()
        
        transactions = manager.grant_subscription_credits(
            user_id="user_123",
            tier="pro",
            subscription_id="sub_123",
        )
        
        assert len(transactions) >= 1
        
        balance = manager.get_balance("user_123", CreditType.APP_GENERATION)
        assert balance.balance == 5  # Pro tier gets 5 app credits
    
    def test_check_and_use_free_operation(self):
        """Test check and use for free operation."""
        manager = CreditManager()
        
        # Add some credits
        manager.add_credits(
            user_id="user_123",
            credit_type=CreditType.DEPLOYMENT,
            amount=5,
            transaction_type=TransactionType.SUBSCRIPTION_GRANT,
            description="Grant",
        )
        
        # Vercel deployment is free
        txn = manager.check_and_use("user_123", "deployment_vercel")
        
        assert txn.amount == 0
        
        balance = manager.get_balance("user_123", CreditType.DEPLOYMENT)
        assert balance.balance == 5  # Unchanged


class TestCreditCosts:
    """Tests for credit cost configuration."""
    
    def test_app_generation_costs(self):
        """Test app generation credit costs."""
        assert CREDIT_COSTS["app_generation_basic"] == 1
        assert CREDIT_COSTS["app_generation_pro"] == 2
        assert CREDIT_COSTS["app_generation_enterprise"] == 3
    
    def test_free_deployments(self):
        """Test that standard deployments are free."""
        assert CREDIT_COSTS["deployment_vercel"] == 0
        assert CREDIT_COSTS["deployment_render"] == 0
    
    def test_business_formation_costs(self):
        """Test business formation credit costs."""
        assert CREDIT_COSTS["llc_formation"] == 10
        assert CREDIT_COSTS["ein_application"] == 5
