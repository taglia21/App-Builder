"""
NexusAI Payments Module

Stripe integration for subscription management, payments, and billing.
"""

from src.payments.stripe_client import (
    StripeClient,
    StripeError,
    PaymentError,
    SubscriptionError,
    CustomerError,
)
from src.payments.subscription import (
    SubscriptionManager,
    SubscriptionTier,
    PricingPlan,
    PRICING_PLANS,
)
from src.payments.webhooks import (
    WebhookHandler,
    WebhookEvent,
    WebhookError,
)
from src.payments.credits import (
    CreditManager,
    CreditTransaction,
    InsufficientCreditsError,
)

__all__ = [
    # Stripe client
    "StripeClient",
    "StripeError",
    "PaymentError",
    "SubscriptionError",
    "CustomerError",
    # Subscription management
    "SubscriptionManager",
    "SubscriptionTier",
    "PricingPlan",
    "PRICING_PLANS",
    # Webhooks
    "WebhookHandler",
    "WebhookEvent",
    "WebhookError",
    # Credits
    "CreditManager",
    "CreditTransaction",
    "InsufficientCreditsError",
]
