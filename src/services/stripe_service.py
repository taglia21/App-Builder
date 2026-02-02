
"""Stripe payment integration service."""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class StripeService:
    """Stripe payment processing service."""
    
    def __init__(self, api_key: str, webhook_secret: Optional[str] = None):
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self._stripe = None
    
    @property
    def stripe(self):
        if self._stripe is None:
            try:
                import stripe
                stripe.api_key = self.api_key
                self._stripe = stripe
            except ImportError:
                raise ImportError("Stripe library not installed. Run: pip install stripe")
        return self._stripe
    
    @classmethod
    def from_settings(cls, settings) -> "StripeService":
        if not settings.STRIPE_SECRET_KEY:
            raise ValueError("STRIPE_SECRET_KEY not configured")
        return cls(settings.STRIPE_SECRET_KEY, settings.STRIPE_WEBHOOK_SECRET)
    
    async def create_customer(self, email: str, name: Optional[str] = None,
                              metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        try:
            customer = self.stripe.Customer.create(email=email, name=name, metadata=metadata or {})
            logger.info(f"Created Stripe customer: {customer.id}")
            return {"id": customer.id, "email": customer.email}
        except self.stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer: {e}")
            raise
    
    async def create_checkout_session(
        self, customer_id: str, price_id: str, success_url: str, cancel_url: str,
        mode: str = "subscription", trial_days: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        try:
            params = {
                "customer": customer_id,
                "payment_method_types": ["card"],
                "line_items": [{"price": price_id, "quantity": 1}],
                "mode": mode,
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": metadata or {},
            }
            if trial_days and mode == "subscription":
                params["subscription_data"] = {"trial_period_days": trial_days}
            session = self.stripe.checkout.Session.create(**params)
            return {"id": session.id, "url": session.url}
        except self.stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout: {e}")
            raise
    
    async def create_billing_portal_session(self, customer_id: str, return_url: str) -> Dict[str, Any]:
        try:
            session = self.stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
            return {"url": session.url}
        except self.stripe.error.StripeError as e:
            logger.error(f"Stripe error creating portal: {e}")
            raise
    
    async def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> Dict[str, Any]:
        try:
            if at_period_end:
                sub = self.stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
            else:
                sub = self.stripe.Subscription.delete(subscription_id)
            return {"id": sub.id, "status": sub.status}
        except self.stripe.error.StripeError as e:
            logger.error(f"Stripe error canceling subscription: {e}")
            raise
    
    async def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        try:
            sub = self.stripe.Subscription.retrieve(subscription_id)
            return {
                "id": sub.id, "status": sub.status, "customer": sub.customer,
                "current_period_end": datetime.fromtimestamp(sub.current_period_end, tz=timezone.utc),
                "cancel_at_period_end": sub.cancel_at_period_end,
            }
        except self.stripe.error.StripeError as e:
            logger.error(f"Stripe error getting subscription: {e}")
            raise
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> Dict[str, Any]:
        if not self.webhook_secret:
            raise ValueError("Webhook secret not configured")
        try:
            event = self.stripe.Webhook.construct_event(payload, signature, self.webhook_secret)
            return {"type": event.type, "data": event.data.object}
        except self.stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise
