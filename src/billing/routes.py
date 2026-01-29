"""Billing routes for subscription management."""
import os
import stripe
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from ..templates import templates

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Price IDs from environment
PRICE_IDS = {
    "starter": os.getenv("STRIPE_PRICE_STARTER"),
    "growth": os.getenv("STRIPE_PRICE_GROWTH"),
    "pro": os.getenv("STRIPE_PRICE_PRO")
}

def create_billing_router(templates):
    router = APIRouter(tags=["billing"])
    
    @router.get("/plans", response_class=HTMLResponse)
    async def pricing_page(request: Request):
        """Display the pricing page."""
        return templates.TemplateResponse(
            "pages/pricing.html",
            {
                "request": request,
                "plans": [
                    {"name": "Starter", "price": 9, "features": ["5 apps/month", "Basic templates", "Email support"]},
                    {"name": "Growth", "price": 49, "features": ["25 apps/month", "All templates", "Priority support", "Custom domains"]},
                    {"name": "Pro", "price": 99, "features": ["Unlimited apps", "All features", "24/7 support", "White-label", "API access"]}
                ]
            }
        )
    
    @router.post("/webhook")
    async def stripe_webhook(request: Request):
        """Handle Stripe webhook events."""
        return {"status": "received"}
    
    return router
