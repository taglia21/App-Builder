import os
import stripe
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

class StripePaymentService:
    """Real Stripe payment processing service."""
    
    def __init__(self):
        self.webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    async def create_checkout_session(
        self,
        price_id: str,
        success_url: str,
        cancel_url: str,
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout session for subscription or one-time payment."""
        try:
            session_params = {
                'payment_method_types': ['card'],
                'line_items': [{'price': price_id, 'quantity': 1}],
                'mode': 'subscription' if 'sub' in price_id else 'payment',
                'success_url': success_url,
                'cancel_url': cancel_url,
            }
            
            if customer_email:
                session_params['customer_email'] = customer_email
            if metadata:
                session_params['metadata'] = metadata
            
            session = stripe.checkout.Session.create(**session_params)
            
            return {
                'success': True,
                'session_id': session.id,
                'url': session.url
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def create_customer(self, email: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Create a Stripe customer."""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name
            )
            return {
                'success': True,
                'customer_id': customer.id
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def create_subscription(
        self,
        customer_id: str,
        price_id: str
    ) -> Dict[str, Any]:
        """Create a subscription for a customer."""
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': price_id}],
                payment_behavior='default_incomplete',
                expand=['latest_invoice.payment_intent']
            )
            return {
                'success': True,
                'subscription_id': subscription.id,
                'status': subscription.status,
                'client_secret': subscription.latest_invoice.payment_intent.client_secret
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def create_one_time_payment(
        self,
        amount: int,
        currency: str = 'usd',
        description: str = 'LaunchForge App Build'
    ) -> Dict[str, Any]:
        """Create a one-time payment intent."""
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                description=description,
                automatic_payment_methods={'enabled': True}
            )
            return {
                'success': True,
                'payment_intent_id': intent.id,
                'client_secret': intent.client_secret
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment intent error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def verify_webhook(self, payload: bytes, sig_header: str) -> Optional[Dict]:
        """Verify and parse a Stripe webhook."""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            return event
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.error(f"Webhook verification failed: {str(e)}")
            return None


# Singleton instance
stripe_payments = StripePaymentService()
