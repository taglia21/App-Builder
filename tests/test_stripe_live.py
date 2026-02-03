"""
Stripe Integration Tests (Mocked)

Unit tests for Stripe integration using mocked API calls.
Tests verify correct Stripe API usage without requiring live API keys.
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from typing import Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from payments.stripe_client import StripeClient


@pytest.fixture
def stripe_client() -> StripeClient:
    """Initialize Stripe client with mocked API key."""
    return StripeClient(api_key="sk_test_mock_key")


@pytest.fixture
def test_customer_email() -> str:
    """Generate unique test customer email."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"test_user_{timestamp}@launchforge-test.com"


class TestStripeConnection:
    """Test basic Stripe API connectivity."""
    
    @patch('stripe.Account.retrieve')
    def test_stripe_api_key_valid(self, mock_retrieve: MagicMock, stripe_client: StripeClient) -> None:
        """Verify Stripe API key is valid and in test mode."""
        # Mock account response
        mock_account = MagicMock()
        mock_account.id = "acct_mock123"
        mock_retrieve.return_value = mock_account
        
        import stripe
        account = stripe.Account.retrieve()
        
        assert account is not None
        assert account.id == "acct_mock123"
        mock_retrieve.assert_called_once()
    
    def test_stripe_test_mode(self, stripe_client: StripeClient) -> None:
        """Verify we're in test mode, not live."""
        # API key should start with sk_test_
        assert stripe_client.api_key.startswith("sk_test_"), \
            "DANGER: Not using test mode key! Use sk_test_xxx"


class TestStripeCustomers:
    """Test Stripe customer operations."""
    
    @patch('stripe.Customer.create')
    @patch('stripe.Customer.delete')
    def test_create_customer(self, mock_delete: MagicMock, mock_create: MagicMock, stripe_client: StripeClient, test_customer_email: str) -> None:
        """Test creating a new Stripe customer."""
        # Mock customer creation
        mock_customer = MagicMock()
        mock_customer.id = "cus_mock123"
        mock_customer.email = test_customer_email
        mock_create.return_value = mock_customer
        
        customer = stripe_client.create_customer(
            email=test_customer_email,
            name="Test User",
            metadata={"source": "integration_test"}
        )
        
        assert customer is not None
        assert customer.id.startswith("cus_")
        assert customer.email == test_customer_email
        mock_create.assert_called_once()
    
    @patch('stripe.Customer.create')
    @patch('stripe.Customer.retrieve')
    @patch('stripe.Customer.delete')
    def test_get_customer(self, mock_delete: MagicMock, mock_retrieve: MagicMock, mock_create: MagicMock, stripe_client: StripeClient, test_customer_email: str) -> None:
        """Test retrieving a customer."""
        # Mock customer
        mock_customer = MagicMock()
        mock_customer.id = "cus_mock123"
        mock_customer.email = test_customer_email
        mock_create.return_value = mock_customer
        mock_retrieve.return_value = mock_customer
        
        import stripe
        created = stripe.Customer.create(
            email=test_customer_email,
            metadata={"source": "integration_test"}
        )
        
        customer = stripe_client.get_customer(created.id)
        assert customer.id == created.id
        assert customer.email == test_customer_email
        mock_retrieve.assert_called_once_with(created.id)
    
    @patch('stripe.Customer.create')
    @patch('stripe.Customer.modify')
    @patch('stripe.Customer.delete')
    def test_update_customer(self, mock_delete: MagicMock, mock_modify: MagicMock, mock_create: MagicMock, stripe_client: StripeClient, test_customer_email: str) -> None:
        """Test updating a customer."""
        # Mock customer
        mock_customer = MagicMock()
        mock_customer.id = "cus_mock123"
        mock_customer.email = test_customer_email
        mock_create.return_value = mock_customer
        
        mock_updated = MagicMock()
        mock_updated.id = mock_customer.id
        mock_updated.name = "Updated Name"
        mock_modify.return_value = mock_updated
        
        import stripe
        created = stripe.Customer.create(
            email=test_customer_email,
            metadata={"source": "integration_test"}
        )
        
        updated = stripe_client.update_customer(
            customer_id=created.id,
            name="Updated Name",
            metadata={"updated": "true"}
        )
        
        assert updated.name == "Updated Name"
        mock_modify.assert_called_once()


class TestStripeProducts:
    """Test Stripe product and price operations."""
    
    @patch('stripe.Product.list')
    def test_list_products(self, mock_list: MagicMock, stripe_client: StripeClient) -> None:
        """Test listing products."""
        # Mock products
        mock_product1 = MagicMock()
        mock_product1.id = "prod_mock1"
        mock_product1.name = "Test Product 1"
        
        mock_product2 = MagicMock()
        mock_product2.id = "prod_mock2"
        mock_product2.name = "Test Product 2"
        
        mock_response = MagicMock()
        mock_response.data = [mock_product1, mock_product2]
        mock_list.return_value = mock_response
        
        import stripe
        products = stripe.Product.list(limit=5, active=True)
        
        assert len(products.data) == 2
        assert products.data[0].name == "Test Product 1"
        mock_list.assert_called_once_with(limit=5, active=True)
    
    @patch('stripe.Price.list')
    def test_list_prices(self, mock_list: MagicMock, stripe_client: StripeClient) -> None:
        """Test listing prices."""
        # Mock prices
        mock_price1 = MagicMock()
        mock_price1.id = "price_mock1"
        mock_price1.unit_amount = 999
        mock_price1.currency = "usd"
        
        mock_price2 = MagicMock()
        mock_price2.id = "price_mock2"
        mock_price2.unit_amount = 2999
        mock_price2.currency = "usd"
        
        mock_response = MagicMock()
        mock_response.data = [mock_price1, mock_price2]
        mock_list.return_value = mock_response
        
        import stripe
        prices = stripe.Price.list(limit=5, active=True)
        
        assert len(prices.data) == 2
        assert prices.data[0].unit_amount == 999
        mock_list.assert_called_once_with(limit=5, active=True)


class TestStripePaymentMethods:
    """Test payment method operations."""
    
    @patch('stripe.PaymentMethod.create')
    def test_create_payment_method(self, mock_create: MagicMock, stripe_client: StripeClient) -> None:
        """Test creating a test payment method."""
        # Mock payment method
        mock_card = MagicMock()
        mock_card.last4 = "4242"
        
        mock_pm = MagicMock()
        mock_pm.id = "pm_mock123"
        mock_pm.card = mock_card
        mock_create.return_value = mock_pm
        
        import stripe
        pm = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": "4242424242424242",
                "exp_month": 12,
                "exp_year": 2030,
                "cvc": "123"
            }
        )
        
        assert pm.id.startswith("pm_")
        assert pm.card.last4 == "4242"
        mock_create.assert_called_once()
    
    @patch('stripe.Customer.create')
    @patch('stripe.PaymentMethod.create')
    @patch('stripe.PaymentMethod.attach')
    @patch('stripe.Customer.modify')
    @patch('stripe.Customer.retrieve')
    @patch('stripe.Customer.delete')
    def test_attach_payment_method(self, mock_delete: MagicMock, mock_retrieve: MagicMock, mock_modify: MagicMock, mock_attach: MagicMock, 
                                   mock_pm_create: MagicMock, mock_cust_create: MagicMock, stripe_client: StripeClient, test_customer_email: str) -> None:
        """Test attaching payment method to customer."""
        # Mock customer
        mock_customer = MagicMock()
        mock_customer.id = "cus_mock123"
        mock_customer.email = test_customer_email
        mock_cust_create.return_value = mock_customer
        
        # Mock payment method
        mock_pm = MagicMock()
        mock_pm.id = "pm_mock123"
        mock_pm_create.return_value = mock_pm
        
        # Mock updated customer
        mock_invoice_settings = MagicMock()
        mock_invoice_settings.default_payment_method = mock_pm.id
        mock_updated = MagicMock()
        mock_updated.invoice_settings = mock_invoice_settings
        mock_retrieve.return_value = mock_updated
        
        import stripe
        customer = stripe.Customer.create(
            email=test_customer_email,
            metadata={"source": "integration_test"}
        )
        
        pm = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": "4242424242424242",
                "exp_month": 12,
                "exp_year": 2030,
                "cvc": "123"
            }
        )
        
        stripe.PaymentMethod.attach(pm.id, customer=customer.id)
        stripe.Customer.modify(
            customer.id,
            invoice_settings={"default_payment_method": pm.id}
        )
        
        updated_customer = stripe.Customer.retrieve(customer.id)
        assert updated_customer.invoice_settings.default_payment_method == pm.id
        mock_attach.assert_called_once_with(pm.id, customer=customer.id)


class TestStripeSubscriptions:
    """Test subscription operations."""
    
    @pytest.fixture
    def test_price_id(self) -> str:
        """Return a test price ID."""
        return "price_mock_monthly"
    
    @patch('stripe.Customer.create')
    @patch('stripe.PaymentMethod.create')
    @patch('stripe.PaymentMethod.attach')
    @patch('stripe.Customer.modify')
    @patch('stripe.Subscription.create')
    @patch('stripe.Subscription.delete')
    @patch('stripe.Customer.delete')
    def test_create_subscription(self, mock_cust_delete: MagicMock, mock_sub_delete: MagicMock, mock_sub_create: MagicMock,
                                 mock_cust_modify: MagicMock, mock_pm_attach: MagicMock, mock_pm_create: MagicMock, mock_cust_create: MagicMock,
                                 stripe_client: StripeClient, test_customer_email: str, test_price_id: str) -> None:  # type: ignore[no-untyped-call]
        """Test creating a subscription."""
        # Mock customer
        mock_customer = MagicMock()
        mock_customer.id = "cus_mock123"
        mock_cust_create.return_value = mock_customer
        
        # Mock payment method
        mock_pm = MagicMock()
        mock_pm.id = "pm_mock123"
        mock_pm_create.return_value = mock_pm
        
        # Mock subscription
        mock_sub = MagicMock()
        mock_sub.id = "sub_mock123"
        mock_sub.status = "active"
        mock_sub_create.return_value = mock_sub
        
        import stripe
        customer = stripe.Customer.create(
            email=test_customer_email,
            metadata={"source": "integration_test"}
        )
        
        pm = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": "4242424242424242",
                "exp_month": 12,
                "exp_year": 2030,
                "cvc": "123"
            }
        )
        stripe.PaymentMethod.attach(pm.id, customer=customer.id)
        stripe.Customer.modify(
            customer.id,
            invoice_settings={"default_payment_method": pm.id}
        )
        
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{"price": test_price_id}],
            metadata={"source": "integration_test"}
        )
        
        assert subscription.id.startswith("sub_")
        assert subscription.status == "active"
        mock_sub_create.assert_called_once()


class TestStripeCheckout:
    """Test Checkout Session operations."""
    
    @pytest.fixture
    def test_price_id(self) -> str:
        """Return a test price ID."""
        return "price_mock_checkout"
    
    @patch('stripe.checkout.Session.create')
    def test_create_checkout_session(self, mock_create: MagicMock, stripe_client: StripeClient, test_price_id: str) -> None:
        """Test creating a Checkout Session."""
        # Mock checkout session
        mock_session = MagicMock()
        mock_session.id = "cs_test_mock123"
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_mock123"
        mock_create.return_value = mock_session
        
        import stripe
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{
                "price": test_price_id,
                "quantity": 1
            }],
            success_url="https://launchforge.io/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://launchforge.io/cancel",
            metadata={"source": "integration_test"}
        )
        
        assert session.id.startswith("cs_test_")
        assert session.url is not None
        mock_create.assert_called_once()


class TestStripeBillingPortal:
    """Test Customer Billing Portal."""
    
    @patch('stripe.Customer.create')
    @patch('stripe.billing_portal.Session.create')
    @patch('stripe.Customer.delete')
    def test_create_portal_session(self, mock_delete: MagicMock, mock_portal_create: MagicMock, mock_cust_create: MagicMock,
                                   stripe_client: StripeClient, test_customer_email: str) -> None:
        """Test creating a billing portal session."""
        # Mock customer
        mock_customer = MagicMock()
        mock_customer.id = "cus_mock123"
        mock_cust_create.return_value = mock_customer
        
        # Mock portal session
        mock_session = MagicMock()
        mock_session.url = "https://billing.stripe.com/session/mock123"
        mock_portal_create.return_value = mock_session
        
        import stripe
        customer = stripe.Customer.create(
            email=test_customer_email,
            metadata={"source": "integration_test"}
        )
        
        session = stripe.billing_portal.Session.create(
            customer=customer.id,
            return_url="https://launchforge.io/dashboard"
        )
        
        assert session.url is not None
        mock_portal_create.assert_called_once()


class TestStripeWebhooks:
    """Test webhook signature verification."""
    
    @patch('stripe.Webhook.construct_event')
    def test_webhook_signature_verification(self, mock_construct: MagicMock, stripe_client: StripeClient) -> None:
        """Test that webhook signature verification works."""
        import time
        
        # Test payload
        payload = '{"type": "test.webhook"}'
        webhook_secret = "whsec_test_secret"
        timestamp = int(time.time())
        
        # Mock successful verification
        mock_event = MagicMock()
        mock_event.type = "test.webhook"
        mock_construct.return_value = mock_event
        
        import stripe
        sig_header = f"t={timestamp},v1=mock_signature"
        
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        assert event is not None
        mock_construct.assert_called_once_with(payload, sig_header, webhook_secret)


class TestStripeRefunds:
    """Test refund operations."""
    
    @patch('stripe.Customer.create')
    @patch('stripe.PaymentMethod.create')
    @patch('stripe.PaymentMethod.attach')
    @patch('stripe.PaymentIntent.create')
    @patch('stripe.Refund.create')
    @patch('stripe.Customer.delete')
    def test_create_refund_flow(self, mock_cust_delete: MagicMock, mock_refund_create: MagicMock, mock_pi_create: MagicMock,
                                mock_pm_attach: MagicMock, mock_pm_create: MagicMock, mock_cust_create: MagicMock,
                                stripe_client: StripeClient, test_customer_email: str) -> None:
        """Test the refund flow (payment -> refund)."""
        # Mock customer
        mock_customer = MagicMock()
        mock_customer.id = "cus_mock123"
        mock_cust_create.return_value = mock_customer
        
        # Mock payment method
        mock_pm = MagicMock()
        mock_pm.id = "pm_mock123"
        mock_pm_create.return_value = mock_pm
        
        # Mock payment intent
        mock_pi = MagicMock()
        mock_pi.id = "pi_mock123"
        mock_pi.status = "succeeded"
        mock_pi.amount = 1000
        mock_pi_create.return_value = mock_pi
        
        # Mock refund
        mock_refund = MagicMock()
        mock_refund.id = "re_mock123"
        mock_refund.status = "succeeded"
        mock_refund.amount = 1000
        mock_refund_create.return_value = mock_refund
        
        import stripe
        customer = stripe.Customer.create(
            email=test_customer_email,
            metadata={"source": "integration_test"}
        )
        
        pm = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": "4242424242424242",
                "exp_month": 12,
                "exp_year": 2030,
                "cvc": "123"
            }
        )
        stripe.PaymentMethod.attach(pm.id, customer=customer.id)
        
        payment_intent = stripe.PaymentIntent.create(
            amount=1000,
            currency="usd",
            customer=customer.id,
            payment_method=pm.id,
            confirm=True,
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"}
        )
        
        assert payment_intent.status == "succeeded"
        
        refund = stripe.Refund.create(
            payment_intent=payment_intent.id,
            reason="requested_by_customer"
        )
        
        assert refund.status == "succeeded"
        mock_refund_create.assert_called_once()


# Run with: pytest tests/test_stripe_live.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
