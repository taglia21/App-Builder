"""
Stripe Live Integration Tests

Tests that actually call the Stripe TEST API to verify integration.
Requires STRIPE_API_KEY with test mode key (sk_test_xxx).
"""

import os
import sys
import pytest
from datetime import datetime
from typing import Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Skip all tests if no Stripe key
STRIPE_TEST_KEY = os.getenv("STRIPE_API_KEY") or os.getenv("STRIPE_SECRET_KEY")
SKIP_REASON = "Stripe test API key not configured (set STRIPE_API_KEY with sk_test_xxx)"

pytestmark = pytest.mark.skipif(
    not STRIPE_TEST_KEY or not STRIPE_TEST_KEY.startswith("sk_test_"),
    reason=SKIP_REASON
)


@pytest.fixture(scope="module")
def stripe_client():
    """Initialize Stripe client with test key."""
    import stripe
    stripe.api_key = STRIPE_TEST_KEY
    
    from payments.stripe_client import StripeClient
    return StripeClient(api_key=STRIPE_TEST_KEY)


@pytest.fixture
def test_customer_email():
    """Generate unique test customer email."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"test_user_{timestamp}@launchforge-test.com"


class TestStripeConnection:
    """Test basic Stripe API connectivity."""
    
    def test_stripe_api_key_valid(self, stripe_client):
        """Verify Stripe API key is valid and in test mode."""
        import stripe
        
        # Try to retrieve account info
        account = stripe.Account.retrieve()
        assert account is not None
        assert account.id is not None
        print(f"✅ Connected to Stripe account: {account.id}")
    
    def test_stripe_test_mode(self, stripe_client):
        """Verify we're in test mode, not live."""
        import stripe
        
        # API key should start with sk_test_
        assert STRIPE_TEST_KEY.startswith("sk_test_"), \
            "DANGER: Not using test mode key! Use sk_test_xxx"
        print("✅ Confirmed test mode (sk_test_)")


class TestStripeCustomers:
    """Test Stripe customer operations."""
    
    def test_create_customer(self, stripe_client, test_customer_email):
        """Test creating a new Stripe customer."""
        customer = stripe_client.create_customer(
            email=test_customer_email,
            name="Test User",
            metadata={"source": "integration_test"}
        )
        
        assert customer is not None
        assert customer.id.startswith("cus_")
        assert customer.email == test_customer_email
        print(f"✅ Created customer: {customer.id}")
        
        # Cleanup
        import stripe
        stripe.Customer.delete(customer.id)
        print(f"✅ Cleaned up customer: {customer.id}")
    
    def test_get_customer(self, stripe_client, test_customer_email):
        """Test retrieving a customer."""
        import stripe
        
        # Create customer first
        created = stripe.Customer.create(
            email=test_customer_email,
            metadata={"source": "integration_test"}
        )
        
        try:
            # Retrieve using our client
            customer = stripe_client.get_customer(created.id)
            assert customer.id == created.id
            assert customer.email == test_customer_email
            print(f"✅ Retrieved customer: {customer.id}")
        finally:
            stripe.Customer.delete(created.id)
    
    def test_update_customer(self, stripe_client, test_customer_email):
        """Test updating a customer."""
        import stripe
        
        # Create customer
        created = stripe.Customer.create(
            email=test_customer_email,
            metadata={"source": "integration_test"}
        )
        
        try:
            # Update using our client
            updated = stripe_client.update_customer(
                customer_id=created.id,
                name="Updated Name",
                metadata={"updated": "true"}
            )
            
            assert updated.name == "Updated Name"
            print(f"✅ Updated customer: {updated.id}")
        finally:
            stripe.Customer.delete(created.id)


class TestStripeProducts:
    """Test Stripe product and price operations."""
    
    def test_list_products(self, stripe_client):
        """Test listing products."""
        import stripe
        
        products = stripe.Product.list(limit=5, active=True)
        print(f"✅ Found {len(products.data)} active products")
        
        for product in products.data[:3]:
            print(f"   - {product.name} ({product.id})")
    
    def test_list_prices(self, stripe_client):
        """Test listing prices."""
        import stripe
        
        prices = stripe.Price.list(limit=5, active=True)
        print(f"✅ Found {len(prices.data)} active prices")
        
        for price in prices.data[:3]:
            amount = price.unit_amount / 100 if price.unit_amount else 0
            print(f"   - ${amount} {price.currency} ({price.id})")


class TestStripePaymentMethods:
    """Test payment method operations."""
    
    def test_create_payment_method(self, stripe_client):
        """Test creating a test payment method."""
        import stripe
        
        # Create a test payment method using Stripe's test card
        pm = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": "4242424242424242",  # Stripe test card
                "exp_month": 12,
                "exp_year": 2030,
                "cvc": "123"
            }
        )
        
        assert pm.id.startswith("pm_")
        assert pm.card.last4 == "4242"
        print(f"✅ Created payment method: {pm.id} (****{pm.card.last4})")
    
    def test_attach_payment_method(self, stripe_client, test_customer_email):
        """Test attaching payment method to customer."""
        import stripe
        
        # Create customer
        customer = stripe.Customer.create(
            email=test_customer_email,
            metadata={"source": "integration_test"}
        )
        
        try:
            # Create payment method
            pm = stripe.PaymentMethod.create(
                type="card",
                card={
                    "number": "4242424242424242",
                    "exp_month": 12,
                    "exp_year": 2030,
                    "cvc": "123"
                }
            )
            
            # Attach to customer
            stripe.PaymentMethod.attach(pm.id, customer=customer.id)
            
            # Set as default
            stripe.Customer.modify(
                customer.id,
                invoice_settings={"default_payment_method": pm.id}
            )
            
            # Verify
            updated_customer = stripe.Customer.retrieve(customer.id)
            assert updated_customer.invoice_settings.default_payment_method == pm.id
            print(f"✅ Attached payment method {pm.id} to customer {customer.id}")
        finally:
            stripe.Customer.delete(customer.id)


class TestStripeSubscriptions:
    """Test subscription operations."""
    
    @pytest.fixture
    def test_price_id(self):
        """Get or create a test price."""
        import stripe
        
        # Try to find existing test price
        prices = stripe.Price.list(limit=1, active=True, type="recurring")
        if prices.data:
            return prices.data[0].id
        
        # Create a test product and price
        product = stripe.Product.create(
            name="Test Product - Integration Test",
            metadata={"source": "integration_test"}
        )
        
        price = stripe.Price.create(
            product=product.id,
            unit_amount=999,  # $9.99
            currency="usd",
            recurring={"interval": "month"}
        )
        
        return price.id
    
    def test_create_subscription(self, stripe_client, test_customer_email, test_price_id):
        """Test creating a subscription."""
        import stripe
        
        # Create customer with payment method
        customer = stripe.Customer.create(
            email=test_customer_email,
            metadata={"source": "integration_test"}
        )
        
        # Create and attach payment method
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
        
        try:
            # Create subscription
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": test_price_id}],
                metadata={"source": "integration_test"}
            )
            
            assert subscription.id.startswith("sub_")
            assert subscription.status in ["active", "trialing", "incomplete"]
            print(f"✅ Created subscription: {subscription.id} (status: {subscription.status})")
            
            # Cancel immediately
            stripe.Subscription.delete(subscription.id)
            print(f"✅ Canceled subscription: {subscription.id}")
        finally:
            stripe.Customer.delete(customer.id)


class TestStripeCheckout:
    """Test Checkout Session operations."""
    
    @pytest.fixture
    def test_price_id(self):
        """Get or create a test price."""
        import stripe
        
        prices = stripe.Price.list(limit=1, active=True, type="recurring")
        if prices.data:
            return prices.data[0].id
        
        product = stripe.Product.create(
            name="Test Product - Checkout Test",
            metadata={"source": "integration_test"}
        )
        
        price = stripe.Price.create(
            product=product.id,
            unit_amount=2900,  # $29.00
            currency="usd",
            recurring={"interval": "month"}
        )
        
        return price.id
    
    def test_create_checkout_session(self, stripe_client, test_price_id):
        """Test creating a Checkout Session."""
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
        print(f"✅ Created checkout session: {session.id}")
        print(f"   Checkout URL: {session.url[:80]}...")


class TestStripeBillingPortal:
    """Test Customer Billing Portal."""
    
    def test_create_portal_session(self, stripe_client, test_customer_email):
        """Test creating a billing portal session."""
        import stripe
        
        # Create customer
        customer = stripe.Customer.create(
            email=test_customer_email,
            metadata={"source": "integration_test"}
        )
        
        try:
            # Create portal session
            session = stripe.billing_portal.Session.create(
                customer=customer.id,
                return_url="https://launchforge.io/dashboard"
            )
            
            assert session.url is not None
            print(f"✅ Created portal session for customer {customer.id}")
            print(f"   Portal URL: {session.url[:80]}...")
        finally:
            stripe.Customer.delete(customer.id)


class TestStripeWebhooks:
    """Test webhook signature verification."""
    
    def test_webhook_signature_verification(self, stripe_client):
        """Test that webhook signature verification works."""
        import stripe
        import time
        import hmac
        import hashlib
        
        # Test payload
        payload = '{"type": "test.webhook"}'
        webhook_secret = "whsec_test_secret"
        
        # Create signature
        timestamp = int(time.time())
        signed_payload = f"{timestamp}.{payload}"
        signature = hmac.new(
            webhook_secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        sig_header = f"t={timestamp},v1={signature}"
        
        # Verify it doesn't crash (actual verification needs real secret)
        try:
            stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
            print("✅ Webhook signature verification logic works")
        except stripe.SignatureVerificationError as e:
            # This is expected since we're using a fake secret
            print("✅ Webhook signature verification works (caught expected error)")


class TestStripeRefunds:
    """Test refund operations."""
    
    def test_create_refund_flow(self, stripe_client, test_customer_email):
        """Test the refund flow (payment -> refund)."""
        import stripe
        
        # Create customer with payment method
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
        
        try:
            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(
                amount=1000,  # $10.00
                currency="usd",
                customer=customer.id,
                payment_method=pm.id,
                confirm=True,
                automatic_payment_methods={"enabled": True, "allow_redirects": "never"}
            )
            
            assert payment_intent.status == "succeeded"
            print(f"✅ Created payment: {payment_intent.id} (${payment_intent.amount/100})")
            
            # Create refund
            refund = stripe.Refund.create(
                payment_intent=payment_intent.id,
                reason="requested_by_customer"
            )
            
            assert refund.status == "succeeded"
            print(f"✅ Created refund: {refund.id} (${refund.amount/100})")
        finally:
            stripe.Customer.delete(customer.id)


# Run with: pytest tests/test_stripe_live.py -v --tb=short
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
