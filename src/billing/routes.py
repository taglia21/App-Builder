"""Billing routes for subscription management with Stripe Checkout."""
import os
import stripe
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from typing import Optional

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Price IDs from environment
PRICE_IDS = {
    "starter": os.getenv("STRIPE_PRICE_STARTER"),
    "growth": os.getenv("STRIPE_PRICE_GROWTH"),
    "pro": os.getenv("STRIPE_PRICE_PRO")
}

PLAN_DETAILS = {
    "starter": {"name": "Starter", "price": 9, "features": ["5 apps/month", "Basic templates", "Email support"]},
    "growth": {"name": "Growth", "price": 49, "features": ["25 apps/month", "All templates", "Priority support", "Custom domains"]},
    "pro": {"name": "Pro", "price": 99, "features": ["Unlimited apps", "All features", "24/7 support", "White-label", "API access"]}
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
        """Handle Stripe webhook events."""
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature", "")
        
        try:
            if STRIPE_WEBHOOK_SECRET:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, STRIPE_WEBHOOK_SECRET
                )
            else:
                event = stripe.Event.construct_from(
                    eval(payload.decode()), stripe.api_key
                )
        except (ValueError, stripe.error.SignatureVerificationError):
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Handle events
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            # TODO: Provision subscription for user
            print(f"Checkout completed: {session['id']}")
        elif event["type"] == "customer.subscription.updated":
            subscription = event["data"]["object"]
            print(f"Subscription updated: {subscription['id']}")
        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            print(f"Subscription cancelled: {subscription['id']}")
        
        return JSONResponse({"status": "received"})
    
    return router
