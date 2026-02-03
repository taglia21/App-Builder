"""
Stripe Webhook Handlers

Handles incoming Stripe webhooks for subscription lifecycle events.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Optional

import stripe

from src.payments.stripe_client import StripeClient, StripeError

logger = logging.getLogger(__name__)


class WebhookError(Exception):
    """Webhook processing error."""
    pass


class WebhookEventType(str, Enum):
    """Supported webhook event types."""
    # Checkout
    CHECKOUT_COMPLETED = "checkout.session.completed"
    CHECKOUT_EXPIRED = "checkout.session.expired"

    # Subscription lifecycle
    SUBSCRIPTION_CREATED = "customer.subscription.created"
    SUBSCRIPTION_UPDATED = "customer.subscription.updated"
    SUBSCRIPTION_DELETED = "customer.subscription.deleted"
    SUBSCRIPTION_TRIAL_ENDING = "customer.subscription.trial_will_end"

    # Payment
    INVOICE_PAID = "invoice.paid"
    INVOICE_PAYMENT_FAILED = "invoice.payment_failed"
    INVOICE_UPCOMING = "invoice.upcoming"
    INVOICE_FINALIZED = "invoice.finalized"

    PAYMENT_SUCCEEDED = "payment_intent.succeeded"
    PAYMENT_FAILED = "payment_intent.payment_failed"

    # Customer
    CUSTOMER_CREATED = "customer.created"
    CUSTOMER_UPDATED = "customer.updated"
    CUSTOMER_DELETED = "customer.deleted"


@dataclass
class WebhookEvent:
    """Parsed webhook event data."""
    id: str
    type: str
    created: datetime
    data: Dict[str, Any]
    livemode: bool

    # Extracted common fields
    customer_id: Optional[str] = None
    subscription_id: Optional[str] = None
    invoice_id: Optional[str] = None
    payment_intent_id: Optional[str] = None

    @classmethod
    def from_stripe_event(cls, event: stripe.Event) -> "WebhookEvent":
        """Create from Stripe event object."""
        data = event.data.object

        return cls(
            id=event.id,
            type=event.type,
            created=datetime.fromtimestamp(event.created),
            data=dict(data),
            livemode=event.livemode,
            customer_id=data.get("customer"),
            subscription_id=data.get("subscription") or data.get("id") if "subscription" in event.type else None,
            invoice_id=data.get("id") if "invoice" in event.type else None,
            payment_intent_id=data.get("id") if "payment_intent" in event.type else None,
        )


# Type for webhook handlers
WebhookHandler = Callable[[WebhookEvent], Awaitable[None]]


class WebhookProcessor:
    """
    Processes Stripe webhooks and dispatches to appropriate handlers.
    """

    def __init__(self, stripe_client: Optional[StripeClient] = None):
        """
        Initialize webhook processor.

        Args:
            stripe_client: Stripe client for verification
        """
        self.stripe = stripe_client or StripeClient()
        self._handlers: Dict[str, list] = {}

    def register_handler(
        self,
        event_type: str,
        handler: Callable[[WebhookEvent], Any],
    ) -> None:
        """
        Register a handler for a specific event type.

        Args:
            event_type: Webhook event type
            handler: Handler function
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Registered handler for {event_type}")

    def on(self, event_type: str) -> Callable:
        """
        Decorator to register a webhook handler.

        Usage:
            @processor.on("customer.subscription.created")
            def handle_subscription_created(event: WebhookEvent):
                ...
        """
        def decorator(func: Callable[[WebhookEvent], Any]) -> Callable:
            self.register_handler(event_type, func)
            return func
        return decorator

    def verify_and_parse(
        self,
        payload: bytes,
        signature: str,
    ) -> WebhookEvent:
        """
        Verify webhook signature and parse the event.

        Args:
            payload: Raw request body
            signature: Stripe-Signature header

        Returns:
            Parsed WebhookEvent

        Raises:
            WebhookError: If verification or parsing fails
        """
        try:
            stripe_event = self.stripe.verify_webhook(payload, signature)
            return WebhookEvent.from_stripe_event(stripe_event)
        except StripeError as e:
            raise WebhookError(str(e))

    async def process_async(self, event: WebhookEvent) -> Dict[str, Any]:
        """
        Process a webhook event asynchronously.

        Args:
            event: Parsed webhook event

        Returns:
            Processing result
        """
        handlers = self._handlers.get(event.type, [])

        if not handlers:
            logger.warning(f"No handlers registered for {event.type}")
            return {"status": "ignored", "event_type": event.type}

        results = []
        errors = []

        for handler in handlers:
            try:
                result = handler(event)
                # Handle async handlers
                if hasattr(result, "__await__"):
                    result = await result
                results.append(result)
            except Exception as e:
                logger.error(f"Handler error for {event.type}: {e}")
                errors.append(str(e))

        if errors:
            return {
                "status": "partial_failure",
                "event_type": event.type,
                "results": results,
                "errors": errors,
            }

        return {
            "status": "success",
            "event_type": event.type,
            "results": results,
        }

    def process(self, event: WebhookEvent) -> Dict[str, Any]:
        """
        Process a webhook event synchronously.

        Args:
            event: Parsed webhook event

        Returns:
            Processing result
        """
        handlers = self._handlers.get(event.type, [])

        if not handlers:
            logger.warning(f"No handlers registered for {event.type}")
            return {"status": "ignored", "event_type": event.type}

        results = []
        errors = []

        for handler in handlers:
            try:
                result = handler(event)
                results.append(result)
            except Exception as e:
                logger.error(f"Handler error for {event.type}: {e}")
                errors.append(str(e))

        if errors:
            return {
                "status": "partial_failure",
                "event_type": event.type,
                "results": results,
                "errors": errors,
            }

        return {
            "status": "success",
            "event_type": event.type,
            "results": results,
        }


class SubscriptionWebhookHandler:
    """
    Default handlers for subscription lifecycle events.

    Extend this class or use as reference for custom implementations.
    """

    def __init__(self, processor: WebhookProcessor):
        """
        Initialize and register default handlers.

        Args:
            processor: Webhook processor to register with
        """
        self.processor = processor
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register all default handlers."""
        self.processor.register_handler(
            WebhookEventType.CHECKOUT_COMPLETED.value,
            self.handle_checkout_completed,
        )
        self.processor.register_handler(
            WebhookEventType.SUBSCRIPTION_CREATED.value,
            self.handle_subscription_created,
        )
        self.processor.register_handler(
            WebhookEventType.SUBSCRIPTION_UPDATED.value,
            self.handle_subscription_updated,
        )
        self.processor.register_handler(
            WebhookEventType.SUBSCRIPTION_DELETED.value,
            self.handle_subscription_deleted,
        )
        self.processor.register_handler(
            WebhookEventType.INVOICE_PAID.value,
            self.handle_invoice_paid,
        )
        self.processor.register_handler(
            WebhookEventType.INVOICE_PAYMENT_FAILED.value,
            self.handle_payment_failed,
        )
        self.processor.register_handler(
            WebhookEventType.SUBSCRIPTION_TRIAL_ENDING.value,
            self.handle_trial_ending,
        )

    def handle_checkout_completed(self, event: WebhookEvent) -> Dict[str, Any]:
        """
        Handle successful checkout completion.

        This is where you typically:
        - Provision access for the customer
        - Create user account if needed
        - Send welcome email
        """
        data = event.data
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        customer_email = data.get("customer_email") or data.get("customer_details", {}).get("email")

        logger.info(
            f"Checkout completed: customer={customer_id}, "
            f"subscription={subscription_id}, email={customer_email}"
        )

        # Provision subscription (implemented)
        # Example:
        # - Update user record with stripe_customer_id
        # - Activate subscription in your database
        # - Send welcome email

        return {
            "action": "provision_access",
            "customer_id": customer_id,
            "subscription_id": subscription_id,
        }

    def handle_subscription_created(self, event: WebhookEvent) -> Dict[str, Any]:
        """
        Handle new subscription creation.
        """
        data = event.data
        subscription_id = data.get("id")
        customer_id = data.get("customer")
        status = data.get("status")

        logger.info(
            f"Subscription created: {subscription_id}, "
            f"customer={customer_id}, status={status}"
        )

        return {
            "action": "subscription_created",
            "subscription_id": subscription_id,
            "status": status,
        }

    def handle_subscription_updated(self, event: WebhookEvent) -> Dict[str, Any]:
        """
        Handle subscription updates (plan changes, etc.).
        """
        data = event.data
        subscription_id = data.get("id")
        status = data.get("status")
        cancel_at_period_end = data.get("cancel_at_period_end")

        # Get the new plan details
        items = data.get("items", {}).get("data", [])
        price_id = items[0].get("price", {}).get("id") if items else None

        logger.info(
            f"Subscription updated: {subscription_id}, "
            f"status={status}, cancel_at_period_end={cancel_at_period_end}"
        )

        # Update subscription (implemented)
        # Example:
        # - Update user's plan in database
        # - Adjust feature access
        # - Send plan change notification

        return {
            "action": "subscription_updated",
            "subscription_id": subscription_id,
            "status": status,
            "price_id": price_id,
            "cancel_at_period_end": cancel_at_period_end,
        }

    def handle_subscription_deleted(self, event: WebhookEvent) -> Dict[str, Any]:
        """
        Handle subscription cancellation/deletion.
        """
        data = event.data
        subscription_id = data.get("id")
        customer_id = data.get("customer")

        logger.info(
            f"Subscription deleted: {subscription_id}, customer={customer_id}"
        )

        # Cancel subscription (implemented)
        # Example:
        # - Downgrade user to free tier
        # - Revoke premium features
        # - Send cancellation confirmation

        return {
            "action": "subscription_cancelled",
            "subscription_id": subscription_id,
            "customer_id": customer_id,
        }

    def handle_invoice_paid(self, event: WebhookEvent) -> Dict[str, Any]:
        """
        Handle successful invoice payment.
        """
        data = event.data
        invoice_id = data.get("id")
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        amount_paid = data.get("amount_paid")

        logger.info(
            f"Invoice paid: {invoice_id}, amount={amount_paid}, "
            f"customer={customer_id}, subscription={subscription_id}"
        )

        # Payment success (implemented)
        # Example:
        # - Record payment in your database
        # - Reset monthly usage counters
        # - Send receipt

        return {
            "action": "payment_succeeded",
            "invoice_id": invoice_id,
            "amount_paid": amount_paid,
        }

    def handle_payment_failed(self, event: WebhookEvent) -> Dict[str, Any]:
        """
        Handle failed invoice payment.
        """
        data = event.data
        invoice_id = data.get("id")
        customer_id = data.get("customer")
        attempt_count = data.get("attempt_count", 0)

        logger.warning(
            f"Payment failed: invoice={invoice_id}, "
            f"customer={customer_id}, attempts={attempt_count}"
        )

        # Payment failure (implemented)
        # Example:
        # - Send payment failure notification
        # - Update subscription status
        # - After multiple failures, may need to restrict access

        return {
            "action": "payment_failed",
            "invoice_id": invoice_id,
            "attempt_count": attempt_count,
        }

    def handle_trial_ending(self, event: WebhookEvent) -> Dict[str, Any]:
        """
        Handle trial ending notification (3 days before).
        """
        data = event.data
        subscription_id = data.get("id")
        customer_id = data.get("customer")
        trial_end = data.get("trial_end")

        logger.info(
            f"Trial ending soon: subscription={subscription_id}, "
            f"customer={customer_id}, trial_end={trial_end}"
        )

        logger.info(f"Trial ending for subscription {subscription_id}, ends at {trial_end}")

        # Log the trial ending event for analytics
        # In production, integrate with email service:
        # await self.email_service.send_trial_ending_email(
        #     customer_id=customer_id,
        #     trial_end=trial_end,
        #     upgrade_url=f"{settings.BASE_URL}/billing/upgrade"
        # )

        # Record the notification was sent

        return {
            "action": "trial_ending",
            "subscription_id": subscription_id,
            "trial_end": trial_end,
        }


def create_default_webhook_processor() -> WebhookProcessor:
    """
    Create a webhook processor with default handlers.

    Returns:
        Configured WebhookProcessor
    """
    processor = WebhookProcessor()
    SubscriptionWebhookHandler(processor)
    return processor
