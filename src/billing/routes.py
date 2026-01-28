"""Billing routes for subscription management."""
import os
import stripe
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from ..auth.dependencies import get_current_user, get_optional_current_user
from ..templates import templates

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Price IDs from environment
PRICE_IDS = {
    "starter": os.getenv("STRIPE_PRICE_STARTER"),
    "growth": os.getenv("STRIPE_PRICE_GROWTH"),
    "pro": os.getenv("STRIPE_PRICE_PRO")
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
            
            # Get base URL for redirect
            base_url = str(request.base_url).rstrip("/")
            
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=f"{base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{base_url}/billing/plans",
                customer_email=user.email if user else None,
                metadata={
                    "user_id": str(user.id) if user else None,
                    "plan": plan
                }
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

    return router
