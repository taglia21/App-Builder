import os
from typing import Optional

import stripe
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Initialize FastAPI
app = FastAPI(
    title="Stripe Payment API", description="API for Stripe payment processing", version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
stripe.webhook_signing_key = os.getenv("STRIPE_WEBHOOK_SECRET")


# Pydantic models
class CheckoutItem(BaseModel):
    price_id: str
    quantity: int


class CheckoutSessionRequest(BaseModel):
    success_url: str
    cancel_url: str
    items: list[CheckoutItem]
    customer_email: Optional[str] = None
    mode: str = "payment"  # or "subscription"
    metadata: Optional[dict] = None


# Error handling
class StripeError(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


# Helper functions
async def verify_stripe_signature(request: Request) -> bool:
    signature = request.headers.get("stripe-signature", "")
    try:
        payload = await request.body()
        stripe.Webhook.construct_event(payload, signature, stripe.webhook_signing_key)
        return True
    except stripe.error.SignatureVerificationError:
        raise StripeError(400, "Invalid Stripe signature")
    except Exception as e:
        raise StripeError(400, f"Webhook error: {str(e)}")


# API Endpoints
@app.post("/create-checkout-session")
async def create_checkout_session(request: CheckoutSessionRequest):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": item.price_id,
                    "quantity": item.quantity,
                }
                for item in request.items
            ],
            mode=request.mode,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            customer_email=request.customer_email,
            metadata=request.metadata,
        )
        return {"session_id": session.id, "url": session.url}
    except stripe.error.StripeError as e:
        raise StripeError(400, str(e))


# Webhook handler
@app.post("/webhook")
async def webhook(request: Request):
    try:
        payload = await request.body()
        event = stripe.Webhook.construct_event(
            payload, request.headers.get("stripe-signature", ""), stripe.webhook_signing_key
        )

        # Handle the checkout.session.completed event
        if event.type == "checkout.session.completed":
            session = event.data.object
            # Handle successful payment
            # Example: Update your database, send confirmation email, etc.
            print(f"Payment succeeded for session {session.id}")

        # Handle the payment_intent.succeeded event
        elif event.type == "payment_intent.succeeded":
            intent = event.data.object
            # Handle successful payment
            # Example: Update your database, send confirmation email, etc.
            print(f"Payment succeeded for intent {intent.id}")

        # Handle the payment_intent.payment_failed event
        elif event.type == "payment_intent.payment_failed":
            intent = event.data.object
            # Handle failed payment
            print(f"Payment failed for intent {intent.id}")

        return JSONResponse(content={"received": True}, status_code=200)

    except stripe.error.SignatureVerificationError:
        raise StripeError(400, "Invalid Stripe signature")
    except Exception as e:
        raise StripeError(400, f"Webhook error: {str(e)}")


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
