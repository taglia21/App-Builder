"""Billing routes for subscription management."""
import os
import stripe
from fastapi import APIRouter, Request, Depends, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse
from ..auth.middleware import get_current_user, get_optional_current_user
from ..templates import templates

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Price IDs from environment
PRICE_IDS = {
    "starter": os.getenv("STRIPE_PRICE_STARTER"),
    "growth": os.getenv("STRIPE_PRICE_GROWTH"),
    "pro": os.getenv("STRIPE_PRICE_PRO")
}

PLAN_NAMES = {
    os.getenv("STRIPE_PRICE_STARTER"): "Starter",
    os.getenv("STRIPE_PRICE_GROWTH"): "Growth",
    os.getenv("STRIPE_PRICE_PRO"): "Pro"
}

def create_billing_router():
    router = APIRouter(prefix="/billing", tags=["billing"])

    @router.get("/", response_class=HTMLResponse)
    async def billing_page(request: Request, user=Depends(get_current_user)):
        """Billing dashboard page."""
        return templates.TemplateResponse(
            "billing/billing.html",
            {"request": request, "user": user}
        )

    @router.get("/plans", response_class=HTMLResponse)
    async def plans_page(request: Request):
        """Pricing plans page."""
        return templates.TemplateResponse(
            "billing/plans.html",
            {"request": request}
        )

    @router.post("/create-checkout-session")
    async def create_checkout_session(
        request: Request,
        user=Depends(get_optional_current_user)
    ):
        """Create a Stripe checkout session for subscription."""
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
                customer_email=user.email if user else None,
                metadata={"user_id": str(user.id) if user else None, "plan": plan}
            )
            return JSONResponse({"url": checkout_session.url})
        except stripe.error.StripeError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/success", response_class=HTMLResponse)
    async def checkout_success(request: Request, session_id: str = None):
        """Successful checkout page."""
        return templates.TemplateResponse(
            "billing/success.html",
            {"request": request, "session_id": session_id}
        )

    @router.post("/webhook")
    async def stripe_webhook(
        request: Request,
        stripe_signature: str = Header(None, alias="Stripe-Signature")
    ):
        """Handle Stripe webhook events."""
        payload = await request.body()
        
        try:
            if STRIPE_WEBHOOK_SECRET:
                event = stripe.Webhook.construct_event(
                    payload, stripe_signature, STRIPE_WEBHOOK_SECRET
                )
            else:
                event = stripe.Event.construct_from(
                    stripe.util.json.loads(payload), stripe.api_key
                )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")

        # Handle subscription events
        if event.type == "checkout.session.completed":
            session = event.data.object
            # Update user subscription status
            print(f"Checkout completed for session: {session.id}")
            # TODO: Update user record with subscription info
            
        elif event.type == "customer.subscription.updated":
            subscription = event.data.object
            print(f"Subscription updated: {subscription.id}")
            
        elif event.type == "customer.subscription.deleted":
            subscription = event.data.object
            print(f"Subscription cancelled: {subscription.id}")
            # TODO: Downgrade user to free tier
            
        elif event.type == "invoice.payment_succeeded":
            invoice = event.data.object
            print(f"Payment succeeded for invoice: {invoice.id}")
            
        elif event.type == "invoice.payment_failed":
            invoice = event.data.object
            print(f"Payment failed for invoice: {invoice.id}")
            # TODO: Notify user of payment failure

        return JSONResponse({"status": "success"})

    return router
