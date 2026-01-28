"""Stripe billing service for subscription management."""
import os
import stripe
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Price IDs for each tier (set these in environment or Stripe dashboard)
PRICE_IDS = {
    "starter": os.getenv("STRIPE_PRICE_STARTER", "price_starter"),
    "professional": os.getenv("STRIPE_PRICE_PROFESSIONAL", "price_professional"),
    "business": os.getenv("STRIPE_PRICE_BUSINESS", "price_business"),
}

TIER_LIMITS = {
    "free": {"app_generations": 0, "price": 0},
    "starter": {"app_generations": 1, "price": 4900},  # $49
    "professional": {"app_generations": 5, "price": 14900},  # $149
    "business": {"app_generations": -1, "price": 39900},  # $399, -1 = unlimited
}


class BillingService:
    """Service for handling Stripe billing operations."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_customer(self, user_id: int, email: str, name: str = None) -> str:
        """Create a Stripe customer for a user."""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"user_id": str(user_id)}
            )
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise
    
    async def create_checkout_session(
        self,
        user_id: int,
        tier: str,
        success_url: str,
        cancel_url: str,
        customer_id: str = None
    ) -> Dict[str, Any]:
        """Create a Stripe checkout session for subscription."""
        if tier not in PRICE_IDS:
            raise ValueError(f"Invalid tier: {tier}")
        
        try:
            session_params = {
                "mode": "subscription",
                "payment_method_types": ["card"],
                "line_items": [{
                    "price": PRICE_IDS[tier],
                    "quantity": 1,
                }],
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": {
                    "user_id": str(user_id),
                    "tier": tier
                },
            }
            
            if customer_id:
                session_params["customer"] = customer_id
            
            session = stripe.checkout.Session.create(**session_params)
            return {
                "session_id": session.id,
                "url": session.url
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise
    
    async def create_portal_session(
        self,
        customer_id: str,
        return_url: str
    ) -> str:
        """Create a Stripe customer portal session for managing subscription."""
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return session.url
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create portal session: {e}")
            raise
    
    async def handle_webhook(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """Handle Stripe webhook events."""
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise
        
        # Handle specific events
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            await self._handle_checkout_completed(session)
        elif event["type"] == "customer.subscription.updated":
            subscription = event["data"]["object"]
            await self._handle_subscription_updated(subscription)
        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            await self._handle_subscription_deleted(subscription)
        elif event["type"] == "invoice.payment_failed":
            invoice = event["data"]["object"]
            await self._handle_payment_failed(invoice)
        
        return {"status": "success", "event_type": event["type"]}
    
    async def _handle_checkout_completed(self, session: Dict):
        """Handle successful checkout."""
        user_id = int(session["metadata"]["user_id"])
        tier = session["metadata"]["tier"]
        customer_id = session["customer"]
        subscription_id = session["subscription"]
        
        # Update user's subscription in database
        from src.database.models import Subscription, SubscriptionTier, SubscriptionStatus
        
        # Get or create subscription record
        result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = result.scalar_one_or_none()
        
        if subscription:
            subscription.stripe_customer_id = customer_id
            subscription.stripe_subscription_id = subscription_id
            subscription.tier = SubscriptionTier(tier)
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.app_generations_limit = TIER_LIMITS[tier]["app_generations"]
            subscription.app_generations_used = 0
        else:
            subscription = Subscription(
                user_id=user_id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                tier=SubscriptionTier(tier),
                status=SubscriptionStatus.ACTIVE,
                app_generations_limit=TIER_LIMITS[tier]["app_generations"],
                app_generations_used=0
            )
            self.db.add(subscription)
        
        await self.db.commit()
        logger.info(f"Subscription activated for user {user_id}: {tier}")
    
    async def _handle_subscription_updated(self, subscription: Dict):
        """Handle subscription updates."""
        from src.database.models import Subscription, SubscriptionStatus
        
        stripe_sub_id = subscription["id"]
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_sub_id
            )
        )
        sub = result.scalar_one_or_none()
        
        if sub:
            status_map = {
                "active": SubscriptionStatus.ACTIVE,
                "past_due": SubscriptionStatus.PAST_DUE,
                "canceled": SubscriptionStatus.CANCELED,
                "trialing": SubscriptionStatus.TRIALING,
                "paused": SubscriptionStatus.PAUSED,
            }
            sub.status = status_map.get(subscription["status"], SubscriptionStatus.ACTIVE)
            sub.cancel_at_period_end = subscription.get("cancel_at_period_end", False)
            
            if subscription.get("current_period_start"):
                sub.current_period_start = datetime.fromtimestamp(
                    subscription["current_period_start"]
                )
            if subscription.get("current_period_end"):
                sub.current_period_end = datetime.fromtimestamp(
                    subscription["current_period_end"]
                )
            
            await self.db.commit()
    
    async def _handle_subscription_deleted(self, subscription: Dict):
        """Handle subscription cancellation."""
        from src.database.models import Subscription, SubscriptionTier, SubscriptionStatus
        
        stripe_sub_id = subscription["id"]
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_sub_id
            )
        )
        sub = result.scalar_one_or_none()
        
        if sub:
            sub.status = SubscriptionStatus.CANCELED
            sub.tier = SubscriptionTier.FREE
            sub.app_generations_limit = 0
            await self.db.commit()
    
    async def _handle_payment_failed(self, invoice: Dict):
        """Handle failed payment."""
        from src.database.models import Subscription, SubscriptionStatus
        
        customer_id = invoice["customer"]
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.stripe_customer_id == customer_id
            )
        )
        sub = result.scalar_one_or_none()
        
        if sub:
            sub.status = SubscriptionStatus.PAST_DUE
            await self.db.commit()
            # TODO: Send email notification about failed payment
