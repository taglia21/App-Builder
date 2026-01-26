"""
Subscription Management

Handles subscription tiers, pricing, and plan management for NexusAI.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
import os
import logging

from src.payments.stripe_client import StripeClient, StripeSubscription, SubscriptionError

logger = logging.getLogger(__name__)


class SubscriptionTier(str, Enum):
    """Available subscription tiers."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class PricingPlan:
    """Pricing plan configuration."""
    tier: SubscriptionTier
    name: str
    description: str
    price_monthly: int  # in cents
    price_yearly: int  # in cents (with discount)
    stripe_price_id_monthly: Optional[str] = None
    stripe_price_id_yearly: Optional[str] = None
    stripe_product_id: Optional[str] = None
    
    # Features
    apps_per_month: int = 1
    priority_support: bool = False
    api_access: bool = False
    white_label: bool = False
    custom_domains: bool = False
    team_members: int = 1
    deployment_platforms: List[str] = field(default_factory=lambda: ["vercel"])
    
    # Business features
    llc_formation: bool = False
    ein_application: bool = False
    banking_setup: bool = False
    domain_registration: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "tier": self.tier.value,
            "name": self.name,
            "description": self.description,
            "price_monthly": self.price_monthly,
            "price_yearly": self.price_yearly,
            "features": {
                "apps_per_month": self.apps_per_month,
                "priority_support": self.priority_support,
                "api_access": self.api_access,
                "white_label": self.white_label,
                "custom_domains": self.custom_domains,
                "team_members": self.team_members,
                "deployment_platforms": self.deployment_platforms,
                "llc_formation": self.llc_formation,
                "ein_application": self.ein_application,
                "banking_setup": self.banking_setup,
                "domain_registration": self.domain_registration,
            },
        }


# Default pricing plans
PRICING_PLANS: Dict[SubscriptionTier, PricingPlan] = {
    SubscriptionTier.FREE: PricingPlan(
        tier=SubscriptionTier.FREE,
        name="Free",
        description="Perfect for trying out NexusAI",
        price_monthly=0,
        price_yearly=0,
        apps_per_month=1,
        priority_support=False,
        api_access=False,
        white_label=False,
        custom_domains=False,
        team_members=1,
        deployment_platforms=["vercel"],
        llc_formation=False,
        ein_application=False,
        banking_setup=False,
        domain_registration=False,
    ),
    SubscriptionTier.PRO: PricingPlan(
        tier=SubscriptionTier.PRO,
        name="Pro",
        description="For serious builders and indie hackers",
        price_monthly=2900,  # $29
        price_yearly=29000,  # $290 (save ~17%)
        stripe_price_id_monthly=os.getenv("STRIPE_PRO_MONTHLY_PRICE_ID"),
        stripe_price_id_yearly=os.getenv("STRIPE_PRO_YEARLY_PRICE_ID"),
        stripe_product_id=os.getenv("STRIPE_PRO_PRODUCT_ID"),
        apps_per_month=5,
        priority_support=True,
        api_access=False,
        white_label=False,
        custom_domains=True,
        team_members=3,
        deployment_platforms=["vercel", "render", "railway"],
        llc_formation=True,
        ein_application=True,
        banking_setup=False,
        domain_registration=True,
    ),
    SubscriptionTier.ENTERPRISE: PricingPlan(
        tier=SubscriptionTier.ENTERPRISE,
        name="Enterprise",
        description="For agencies and high-volume users",
        price_monthly=9900,  # $99
        price_yearly=99000,  # $990 (save ~17%)
        stripe_price_id_monthly=os.getenv("STRIPE_ENTERPRISE_MONTHLY_PRICE_ID"),
        stripe_price_id_yearly=os.getenv("STRIPE_ENTERPRISE_YEARLY_PRICE_ID"),
        stripe_product_id=os.getenv("STRIPE_ENTERPRISE_PRODUCT_ID"),
        apps_per_month=-1,  # Unlimited
        priority_support=True,
        api_access=True,
        white_label=True,
        custom_domains=True,
        team_members=-1,  # Unlimited
        deployment_platforms=["vercel", "render", "railway", "aws", "gcp"],
        llc_formation=True,
        ein_application=True,
        banking_setup=True,
        domain_registration=True,
    ),
}


@dataclass
class UserSubscription:
    """User's subscription state."""
    user_id: str
    tier: SubscriptionTier
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    status: str = "active"
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    
    # Usage tracking
    apps_created_this_month: int = 0
    usage_reset_date: Optional[datetime] = None
    
    @property
    def plan(self) -> PricingPlan:
        """Get the pricing plan for this tier."""
        return PRICING_PLANS[self.tier]
    
    @property
    def can_create_app(self) -> bool:
        """Check if user can create another app this month."""
        if self.plan.apps_per_month == -1:  # Unlimited
            return True
        return self.apps_created_this_month < self.plan.apps_per_month
    
    @property
    def apps_remaining(self) -> int:
        """Get remaining apps for this month."""
        if self.plan.apps_per_month == -1:
            return -1  # Unlimited
        return max(0, self.plan.apps_per_month - self.apps_created_this_month)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "user_id": self.user_id,
            "tier": self.tier.value,
            "status": self.status,
            "current_period_start": self.current_period_start.isoformat() if self.current_period_start else None,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
            "cancel_at_period_end": self.cancel_at_period_end,
            "apps_created_this_month": self.apps_created_this_month,
            "apps_remaining": self.apps_remaining,
            "plan": self.plan.to_dict(),
        }


class SubscriptionManager:
    """
    Manages user subscriptions and plan enforcement.
    """
    
    def __init__(self, stripe_client: Optional[StripeClient] = None):
        """
        Initialize subscription manager.
        
        Args:
            stripe_client: Stripe client instance (creates one if not provided)
        """
        self.stripe = stripe_client or StripeClient()
    
    def get_plan(self, tier: SubscriptionTier) -> PricingPlan:
        """
        Get a pricing plan by tier.
        
        Args:
            tier: Subscription tier
            
        Returns:
            PricingPlan for the tier
        """
        return PRICING_PLANS[tier]
    
    def get_all_plans(self) -> List[PricingPlan]:
        """
        Get all available pricing plans.
        
        Returns:
            List of all PricingPlan objects
        """
        return list(PRICING_PLANS.values())
    
    def create_subscription(
        self,
        user_id: str,
        email: str,
        tier: SubscriptionTier,
        billing_interval: str = "monthly",
        trial_days: Optional[int] = None,
        name: Optional[str] = None,
    ) -> UserSubscription:
        """
        Create a new subscription for a user.
        
        Args:
            user_id: User ID
            email: User email
            tier: Desired subscription tier
            billing_interval: "monthly" or "yearly"
            trial_days: Number of trial days
            name: Customer name
            
        Returns:
            UserSubscription object
        """
        plan = self.get_plan(tier)
        
        # Free tier doesn't need Stripe
        if tier == SubscriptionTier.FREE:
            return UserSubscription(
                user_id=user_id,
                tier=tier,
                status="active",
                current_period_start=datetime.utcnow(),
            )
        
        # Get the appropriate price ID
        price_id = (
            plan.stripe_price_id_yearly 
            if billing_interval == "yearly" 
            else plan.stripe_price_id_monthly
        )
        
        if not price_id:
            raise SubscriptionError(
                f"No Stripe price configured for {tier.value} {billing_interval}"
            )
        
        # Create Stripe customer
        customer = self.stripe.create_customer(
            email=email,
            name=name,
            metadata={"user_id": user_id, "tier": tier.value},
        )
        
        # Create subscription
        subscription = self.stripe.create_subscription(
            customer_id=customer.id,
            price_id=price_id,
            trial_days=trial_days,
            metadata={"user_id": user_id},
        )
        
        logger.info(f"Created {tier.value} subscription for user {user_id}")
        
        return UserSubscription(
            user_id=user_id,
            tier=tier,
            stripe_customer_id=customer.id,
            stripe_subscription_id=subscription.id,
            status=subscription.status,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
        )
    
    def get_subscription(
        self,
        stripe_subscription_id: str,
        user_id: str,
    ) -> UserSubscription:
        """
        Get a user's subscription details.
        
        Args:
            stripe_subscription_id: Stripe subscription ID
            user_id: User ID
            
        Returns:
            UserSubscription object
        """
        subscription = self.stripe.get_subscription(stripe_subscription_id)
        
        # Determine tier from price ID
        tier = self._tier_from_price_id(subscription.price_id)
        
        return UserSubscription(
            user_id=user_id,
            tier=tier,
            stripe_customer_id=subscription.customer_id,
            stripe_subscription_id=subscription.id,
            status=subscription.status,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
        )
    
    def upgrade_subscription(
        self,
        stripe_subscription_id: str,
        new_tier: SubscriptionTier,
        billing_interval: str = "monthly",
    ) -> StripeSubscription:
        """
        Upgrade a subscription to a higher tier.
        
        Args:
            stripe_subscription_id: Stripe subscription ID
            new_tier: New subscription tier
            billing_interval: "monthly" or "yearly"
            
        Returns:
            Updated StripeSubscription
        """
        plan = self.get_plan(new_tier)
        
        price_id = (
            plan.stripe_price_id_yearly 
            if billing_interval == "yearly" 
            else plan.stripe_price_id_monthly
        )
        
        if not price_id:
            raise SubscriptionError(
                f"No Stripe price configured for {new_tier.value} {billing_interval}"
            )
        
        subscription = self.stripe.update_subscription(
            subscription_id=stripe_subscription_id,
            price_id=price_id,
            proration_behavior="create_prorations",
        )
        
        logger.info(f"Upgraded subscription {stripe_subscription_id} to {new_tier.value}")
        
        return subscription
    
    def downgrade_subscription(
        self,
        stripe_subscription_id: str,
        new_tier: SubscriptionTier,
        billing_interval: str = "monthly",
    ) -> StripeSubscription:
        """
        Downgrade a subscription to a lower tier (takes effect at period end).
        
        Args:
            stripe_subscription_id: Stripe subscription ID
            new_tier: New subscription tier
            billing_interval: "monthly" or "yearly"
            
        Returns:
            Updated StripeSubscription
        """
        plan = self.get_plan(new_tier)
        
        # For downgrade to free, cancel the subscription
        if new_tier == SubscriptionTier.FREE:
            return self.cancel_subscription(stripe_subscription_id, immediately=False)
        
        price_id = (
            plan.stripe_price_id_yearly 
            if billing_interval == "yearly" 
            else plan.stripe_price_id_monthly
        )
        
        if not price_id:
            raise SubscriptionError(
                f"No Stripe price configured for {new_tier.value} {billing_interval}"
            )
        
        # Downgrade takes effect at period end (no proration)
        subscription = self.stripe.update_subscription(
            subscription_id=stripe_subscription_id,
            price_id=price_id,
            proration_behavior="none",
        )
        
        logger.info(f"Scheduled downgrade of {stripe_subscription_id} to {new_tier.value}")
        
        return subscription
    
    def cancel_subscription(
        self,
        stripe_subscription_id: str,
        immediately: bool = False,
    ) -> StripeSubscription:
        """
        Cancel a subscription.
        
        Args:
            stripe_subscription_id: Stripe subscription ID
            immediately: If True, cancel immediately; otherwise at period end
            
        Returns:
            Cancelled StripeSubscription
        """
        subscription = self.stripe.cancel_subscription(
            subscription_id=stripe_subscription_id,
            immediately=immediately,
        )
        
        logger.info(
            f"Cancelled subscription {stripe_subscription_id} "
            f"(immediately={immediately})"
        )
        
        return subscription
    
    def reactivate_subscription(
        self,
        stripe_subscription_id: str,
    ) -> StripeSubscription:
        """
        Reactivate a subscription that was set to cancel at period end.
        
        Args:
            stripe_subscription_id: Stripe subscription ID
            
        Returns:
            Reactivated StripeSubscription
        """
        subscription = self.stripe.update_subscription(
            subscription_id=stripe_subscription_id,
            cancel_at_period_end=False,
        )
        
        logger.info(f"Reactivated subscription: {stripe_subscription_id}")
        
        return subscription
    
    def create_checkout_session(
        self,
        tier: SubscriptionTier,
        success_url: str,
        cancel_url: str,
        customer_id: Optional[str] = None,
        customer_email: Optional[str] = None,
        billing_interval: str = "monthly",
        trial_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout session for subscription signup.
        
        Args:
            tier: Subscription tier
            success_url: URL after successful payment
            cancel_url: URL if payment cancelled
            customer_id: Existing Stripe customer ID
            customer_email: Email for new customer
            billing_interval: "monthly" or "yearly"
            trial_days: Trial period days
            
        Returns:
            Checkout session with URL
        """
        plan = self.get_plan(tier)
        
        if tier == SubscriptionTier.FREE:
            raise SubscriptionError("Cannot checkout for free tier")
        
        price_id = (
            plan.stripe_price_id_yearly 
            if billing_interval == "yearly" 
            else plan.stripe_price_id_monthly
        )
        
        if not price_id:
            raise SubscriptionError(
                f"No Stripe price configured for {tier.value} {billing_interval}"
            )
        
        return self.stripe.create_checkout_session(
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            customer_id=customer_id,
            customer_email=customer_email,
            mode="subscription",
            trial_days=trial_days,
        )
    
    def create_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> Dict[str, Any]:
        """
        Create a customer portal session for self-service management.
        
        Args:
            customer_id: Stripe customer ID
            return_url: URL to return to after portal
            
        Returns:
            Portal session with URL
        """
        return self.stripe.create_portal_session(
            customer_id=customer_id,
            return_url=return_url,
        )
    
    def check_feature_access(
        self,
        user_subscription: UserSubscription,
        feature: str,
    ) -> bool:
        """
        Check if a user has access to a specific feature.
        
        Args:
            user_subscription: User's subscription
            feature: Feature name to check
            
        Returns:
            True if user has access
        """
        plan = user_subscription.plan
        
        feature_map = {
            "priority_support": plan.priority_support,
            "api_access": plan.api_access,
            "white_label": plan.white_label,
            "custom_domains": plan.custom_domains,
            "llc_formation": plan.llc_formation,
            "ein_application": plan.ein_application,
            "banking_setup": plan.banking_setup,
            "domain_registration": plan.domain_registration,
        }
        
        return feature_map.get(feature, False)
    
    def _tier_from_price_id(self, price_id: str) -> SubscriptionTier:
        """Determine subscription tier from Stripe price ID."""
        for tier, plan in PRICING_PLANS.items():
            if price_id in [plan.stripe_price_id_monthly, plan.stripe_price_id_yearly]:
                return tier
        
        # Default to free if unknown
        logger.warning(f"Unknown price ID: {price_id}, defaulting to FREE tier")
        return SubscriptionTier.FREE
