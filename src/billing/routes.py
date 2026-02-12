"""Billing routes for subscription management with Stripe Checkout."""
import json
import logging
import os

try:
    import stripe
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    HAS_STRIPE = True
except ImportError:
    stripe = None
    HAS_STRIPE = False

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

logger = logging.getLogger(__name__)

# Stripe configuration
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Unified price IDs from environment — tier names match SubscriptionTier enum
PRICE_IDS = {
    "starter": os.getenv("STRIPE_PRICE_STARTER"),
    "pro": os.getenv("STRIPE_PRICE_PRO"),
    "enterprise": os.getenv("STRIPE_PRICE_ENTERPRISE"),
}

PLAN_DETAILS = {
    "starter": {"name": "Starter", "price": 29, "features": ["5 apps/month", "Basic templates", "Email support"]},
    "pro": {"name": "Pro", "price": 99, "features": ["25 apps/month", "All templates", "Priority support", "Custom domains"]},
    "enterprise": {"name": "Enterprise", "price": 299, "features": ["Unlimited apps", "All features", "24/7 support", "White-label", "API access"]},
}

def create_billing_router(templates):
    """Create billing router with templates."""
    router = APIRouter(tags=["billing"])

    @router.get("/plans", response_class=HTMLResponse)
    async def pricing_page(request: Request):
        """Display the pricing page."""
        plans = []
        for key, details in PLAN_DETAILS.items():
            plans.append({
                "id": key,
                "name": details["name"],
                "price": details["price"],
                "features": details["features"],
                "price_id": PRICE_IDS.get(key)
            })
        return templates.TemplateResponse(
            "pages/pricing.html",
            {"request": request, "plans": plans}
        )

    @router.post("/create-checkout-session")
    async def create_checkout_session(request: Request):
        """Create a Stripe Checkout session for subscription."""
        try:
            data = await request.json()
            plan = data.get("plan", "starter")
            price_id = PRICE_IDS.get(plan)

            if not price_id:
                raise HTTPException(status_code=400, detail="Invalid plan")

            base_url = str(request.base_url).rstrip("/")

            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                success_url=f"{base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{base_url}/billing/plans",
                allow_promotion_codes=True,
            )
            return JSONResponse({"url": checkout_session.url})
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/success", response_class=HTMLResponse)
    async def checkout_success(request: Request, session_id: str = None):
        """Handle successful checkout."""
        return templates.TemplateResponse(
            "pages/billing_success.html",
            {"request": request, "session_id": session_id}
        )

    @router.get("/portal")
    async def customer_portal(request: Request):
        """Redirect to Stripe Customer Portal for subscription management."""
        # In production, get customer_id from logged-in user
        customer_id = request.query_params.get("customer_id")
        if not customer_id:
            return RedirectResponse("/billing/plans")

        try:
            base_url = str(request.base_url).rstrip("/")
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=f"{base_url}/dashboard",
            )
            return RedirectResponse(session.url)
        except stripe.error.StripeError:
            return RedirectResponse("/billing/plans")

    @router.post("/webhook")
    async def stripe_webhook(request: Request):
        """Handle Stripe webhook events with signature verification and DB provisioning."""
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature", "")

        if not STRIPE_WEBHOOK_SECRET:
            logger.error("STRIPE_WEBHOOK_SECRET not configured — rejecting webhook")
            raise HTTPException(status_code=500, detail="Webhook secret not configured")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            raise HTTPException(status_code=400, detail="Invalid signature")

        # --- Idempotency: check if already processed ---
        try:
            from src.database.db import get_db
            from src.database.models import (
                Subscription, SubscriptionStatus, SubscriptionTier,
                WebhookEvent, User,
            )
            from uuid import uuid4

            db = get_db()
            with db.session() as session:
                existing = session.query(WebhookEvent).filter(
                    WebhookEvent.stripe_event_id == event["id"]
                ).first()
                if existing:
                    logger.info(f"Duplicate webhook {event['id']} — skipping")
                    return JSONResponse({"status": "duplicate"})

                # Record the event
                wh = WebhookEvent(
                    id=str(uuid4()),
                    stripe_event_id=event["id"],
                    event_type=event["type"],
                )
                session.add(wh)

                # --- Provision based on event type ---
                if event["type"] == "checkout.session.completed":
                    sess_obj = event["data"]["object"]
                    user_id = sess_obj.get("metadata", {}).get("user_id")
                    tier_name = sess_obj.get("metadata", {}).get("plan", "pro")
                    customer_id = sess_obj.get("customer")
                    subscription_id = sess_obj.get("subscription")

                    if user_id:
                        sub = session.query(Subscription).filter(
                            Subscription.user_id == user_id
                        ).first()
                        tier_enum = SubscriptionTier(tier_name) if tier_name in [t.value for t in SubscriptionTier] else SubscriptionTier.PRO

                        if sub:
                            sub.stripe_customer_id = customer_id
                            sub.stripe_subscription_id = subscription_id
                            sub.tier = tier_enum
                            sub.status = SubscriptionStatus.ACTIVE
                        else:
                            sub = Subscription(
                                id=str(uuid4()),
                                user_id=user_id,
                                stripe_customer_id=customer_id,
                                stripe_subscription_id=subscription_id,
                                tier=tier_enum,
                                status=SubscriptionStatus.ACTIVE,
                            )
                            session.add(sub)

                        # Update user's tier
                        user = session.query(User).filter(User.id == user_id).first()
                        if user:
                            user.subscription_tier = tier_enum

                    logger.info(f"Checkout completed: {sess_obj.get('id')} — subscription provisioned for user {user_id}")

                elif event["type"] == "customer.subscription.updated":
                    sub_obj = event["data"]["object"]
                    stripe_sub_id = sub_obj["id"]
                    sub = session.query(Subscription).filter(
                        Subscription.stripe_subscription_id == stripe_sub_id
                    ).first()
                    if sub:
                        status_map = {
                            "active": SubscriptionStatus.ACTIVE,
                            "past_due": SubscriptionStatus.PAST_DUE,
                            "canceled": SubscriptionStatus.CANCELED,
                            "trialing": SubscriptionStatus.TRIALING,
                            "paused": SubscriptionStatus.PAUSED,
                        }
                        sub.status = status_map.get(sub_obj["status"], SubscriptionStatus.ACTIVE)
                        sub.cancel_at_period_end = sub_obj.get("cancel_at_period_end", False)
                    logger.info(f"Subscription updated: {stripe_sub_id}")

                elif event["type"] == "customer.subscription.deleted":
                    sub_obj = event["data"]["object"]
                    stripe_sub_id = sub_obj["id"]
                    sub = session.query(Subscription).filter(
                        Subscription.stripe_subscription_id == stripe_sub_id
                    ).first()
                    if sub:
                        sub.status = SubscriptionStatus.CANCELED
                        sub.tier = SubscriptionTier.FREE
                        # Also downgrade the user
                        user = session.query(User).filter(User.id == sub.user_id).first()
                        if user:
                            user.subscription_tier = SubscriptionTier.FREE
                    logger.info(f"Subscription cancelled: {stripe_sub_id}")

                elif event["type"] == "invoice.payment_failed":
                    inv_obj = event["data"]["object"]
                    cust_id = inv_obj["customer"]
                    sub = session.query(Subscription).filter(
                        Subscription.stripe_customer_id == cust_id
                    ).first()
                    if sub:
                        sub.status = SubscriptionStatus.PAST_DUE
                    logger.warning(f"Payment failed for customer {cust_id}")

                wh.processed = True
                session.commit()

        except Exception as e:
            logger.error(f"Error processing webhook {event.get('id', '?')}: {e}", exc_info=True)
            # Still return 200 so Stripe doesn't keep retrying
            return JSONResponse({"status": "error", "message": str(e)})

        return JSONResponse({"status": "received"})
    return router
