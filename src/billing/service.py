"""Stripe billing service for subscription management.

Uses synchronous SQLAlchemy sessions (the project uses sync SQLAlchemy, not async).
Works in Stripe test mode — all stripe.api_key values beginning with 'sk_test_'
will hit the Stripe test environment automatically.
"""
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

import stripe
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stripe configuration
# ---------------------------------------------------------------------------
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Unified price IDs — tier names match SubscriptionTier enum values.
# No hardcoded fallbacks: if env vars are not set the price IDs will be None,
# and create_checkout_session will raise a clear error rather than sending a
# bogus ID to Stripe.
PRICE_IDS = {
    "starter": os.getenv("STRIPE_PRICE_STARTER"),
    "pro": os.getenv("STRIPE_PRICE_PRO"),
    "enterprise": os.getenv("STRIPE_PRICE_ENTERPRISE"),
}

TIER_LIMITS = {
    "free":       {"app_generations": 1,  "price": 0},
    "starter":    {"app_generations": 5,  "price": 2900},   # $29
    "pro":        {"app_generations": 25, "price": 9900},   # $99
    "enterprise": {"app_generations": -1, "price": 29900},  # $299, -1 = unlimited
}


def _stripe_configured() -> bool:
    """Return True if a Stripe secret key is present."""
    return bool(stripe.api_key)


class BillingService:
    """Service for handling Stripe billing operations.

    The ``db_session`` argument should be a synchronous SQLAlchemy
    ``Session`` (not ``AsyncSession``).  Pass ``None`` if the DB is not
    available — the service will still work for Stripe-only operations.
    """

    def __init__(self, db_session: Optional[Session] = None):
        self.db: Optional[Session] = db_session

    # ------------------------------------------------------------------
    # Customer
    # ------------------------------------------------------------------

    def create_customer(self, user_id: str, email: str, name: str = None) -> str:
        """Create a Stripe customer for a user."""
        if not _stripe_configured():
            raise ValueError(
                "Stripe is not configured. Set STRIPE_SECRET_KEY to enable payments."
            )
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"user_id": str(user_id)},
            )
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise

    # ------------------------------------------------------------------
    # Checkout
    # ------------------------------------------------------------------

    def create_checkout_session(
        self,
        user_id: str,
        tier: str,
        success_url: str,
        cancel_url: str,
        customer_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout session for a subscription.

        Works in test mode when ``STRIPE_SECRET_KEY`` begins with ``sk_test_``.
        Returns ``{"session_id": ..., "url": ...}`` on success.
        """
        if not _stripe_configured():
            raise ValueError(
                "Stripe is not configured. Set STRIPE_SECRET_KEY to enable payments."
            )
        if tier not in PRICE_IDS:
            raise ValueError(f"Invalid tier: {tier}. Valid tiers: {list(PRICE_IDS)}")

        price_id = PRICE_IDS.get(tier)
        if not price_id:
            raise ValueError(
                f"Price ID for tier '{tier}' is not configured. "
                f"Set STRIPE_PRICE_{tier.upper()} in your environment."
            )

        try:
            session_params: Dict[str, Any] = {
                "mode": "subscription",
                "payment_method_types": ["card"],
                "line_items": [{"price": price_id, "quantity": 1}],
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": {
                    "user_id": str(user_id),
                    "tier": tier,
                },
                "allow_promotion_codes": True,
            }

            if customer_id:
                session_params["customer"] = customer_id

            session = stripe.checkout.Session.create(**session_params)
            return {"session_id": session.id, "url": session.url}
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise

    # ------------------------------------------------------------------
    # Portal
    # ------------------------------------------------------------------

    def create_portal_session(self, customer_id: str, return_url: str) -> str:
        """Create a Stripe Customer Portal session for managing subscription."""
        if not _stripe_configured():
            raise ValueError(
                "Stripe is not configured. Set STRIPE_SECRET_KEY to enable payments."
            )
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return session.url
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create portal session: {e}")
            raise

    # ------------------------------------------------------------------
    # Webhook
    # ------------------------------------------------------------------

    def handle_webhook(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """Handle Stripe webhook events with idempotency.

        Uses a sync DB session (``self.db``) throughout.  If no DB session is
        available the event is still verified and dispatched but not persisted.
        """
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        if not webhook_secret:
            logger.error("STRIPE_WEBHOOK_SECRET not configured — rejecting webhook")
            raise ValueError("Webhook secret not configured")

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise

        if self.db is not None:
            return self._handle_webhook_with_db(event)

        # No DB — just dispatch without persistence
        return self._dispatch_event(event)

    def _handle_webhook_with_db(self, event) -> Dict[str, Any]:
        """Idempotent webhook handling backed by the sync SQLAlchemy session."""
        from src.database.models import WebhookEvent  # lazy import

        existing = (
            self.db.execute(
                select(WebhookEvent).where(WebhookEvent.stripe_event_id == event["id"])
            )
            .scalar_one_or_none()
        )
        if existing:
            logger.info(f"Duplicate webhook event {event['id']} — skipping")
            return {"status": "duplicate", "event_type": event["type"]}

        # Record the event
        webhook_record = WebhookEvent(
            id=str(uuid4()),
            stripe_event_id=event["id"],
            event_type=event["type"],
            payload=dict(event["data"]["object"]) if event.get("data") else None,
        )
        self.db.add(webhook_record)

        try:
            self._dispatch_event(event)
            webhook_record.processed = True
        except Exception as e:
            webhook_record.error_message = str(e)
            logger.error(f"Error processing webhook {event['id']}: {e}")

        self.db.commit()
        return {"status": "success", "event_type": event["type"]}

    def _dispatch_event(self, event) -> Dict[str, Any]:
        """Route a verified Stripe event to the appropriate handler."""
        event_type = event["type"]
        if event_type == "checkout.session.completed":
            self._handle_checkout_completed(event["data"]["object"])
        elif event_type == "customer.subscription.updated":
            self._handle_subscription_updated(event["data"]["object"])
        elif event_type == "customer.subscription.deleted":
            self._handle_subscription_deleted(event["data"]["object"])
        elif event_type == "invoice.payment_failed":
            self._handle_payment_failed(event["data"]["object"])
        return {"status": "success", "event_type": event_type}

    # ------------------------------------------------------------------
    # Private event handlers (sync)
    # ------------------------------------------------------------------

    def _handle_checkout_completed(self, session: Dict):
        """Handle successful checkout — provision/update subscription in DB."""
        if self.db is None:
            return

        user_id = session.get("metadata", {}).get("user_id")
        tier = session.get("metadata", {}).get("tier", "pro")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")

        if not user_id:
            logger.warning("checkout.session.completed has no user_id in metadata")
            return

        from src.database.models import (  # lazy import to avoid circular deps
            Subscription,
            SubscriptionStatus,
            SubscriptionTier,
        )

        result = self.db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = result.scalar_one_or_none()

        tier_enum = (
            SubscriptionTier(tier)
            if tier in [t.value for t in SubscriptionTier]
            else SubscriptionTier.PRO
        )

        if subscription:
            subscription.stripe_customer_id = customer_id
            subscription.stripe_subscription_id = subscription_id
            subscription.tier = tier_enum
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.app_generations_limit = TIER_LIMITS.get(tier, {}).get(
                "app_generations", 25
            )
        else:
            subscription = Subscription(
                id=str(uuid4()),
                user_id=user_id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                tier=tier_enum,
                status=SubscriptionStatus.ACTIVE,
                app_generations_limit=TIER_LIMITS.get(tier, {}).get(
                    "app_generations", 25
                ),
            )
            self.db.add(subscription)

        self.db.commit()
        logger.info(f"Subscription activated for user {user_id}: {tier}")

    def _handle_subscription_updated(self, subscription: Dict):
        """Handle subscription status/period changes."""
        if self.db is None:
            return

        from src.database.models import Subscription, SubscriptionStatus  # lazy

        stripe_sub_id = subscription["id"]
        result = self.db.execute(
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
                    subscription["current_period_start"], tz=timezone.utc
                )
            if subscription.get("current_period_end"):
                sub.current_period_end = datetime.fromtimestamp(
                    subscription["current_period_end"], tz=timezone.utc
                )

            self.db.commit()

    def _handle_subscription_deleted(self, subscription: Dict):
        """Handle subscription cancellation — downgrade user to free tier."""
        if self.db is None:
            return

        from src.database.models import Subscription, SubscriptionStatus, SubscriptionTier  # lazy

        stripe_sub_id = subscription["id"]
        result = self.db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_sub_id
            )
        )
        sub = result.scalar_one_or_none()

        if sub:
            sub.status = SubscriptionStatus.CANCELED
            sub.tier = SubscriptionTier.FREE
            sub.app_generations_limit = TIER_LIMITS["free"]["app_generations"]
            self.db.commit()

    def _handle_payment_failed(self, invoice: Dict):
        """Handle failed payment — mark subscription as past due."""
        if self.db is None:
            return

        from src.database.models import Subscription, SubscriptionStatus  # lazy

        customer_id = invoice["customer"]
        result = self.db.execute(
            select(Subscription).where(
                Subscription.stripe_customer_id == customer_id
            )
        )
        sub = result.scalar_one_or_none()

        if sub:
            sub.status = SubscriptionStatus.PAST_DUE
            self.db.commit()
            logger.warning(
                f"Payment failed for customer {customer_id}, "
                f"subscription {sub.stripe_subscription_id}. Marked PAST_DUE."
            )
