import logging
import os
from typing import Optional

import stripe
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Initialize FastAPI app
app = FastAPI(
    title="Stripe Payment Service", description="API for handling Stripe payments", version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Stripe API key from environment variables
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

if not STRIPE_SECRET_KEY:
    raise ValueError("Stripe secret key not found in environment variables")

stripe.api_key = STRIPE_SECRET_KEY


# Models
class CheckoutItem(BaseModel):
    price_id: str
    quantity: int = 1


class CreateCheckoutSessionRequest(BaseModel):
    success_url: str
    cancel_url: str
    items: list[CheckoutItem]
    customer_email: Optional[str] = None
    mode: str = "payment"


class WebhookEvent(BaseModel):
    id: str
    object: str
    type: str
    data: dict
    request: Optional[dict] = None


@app.post("/create-checkout-session", response_model=dict)
async def create_checkout_session(request: CreateCheckoutSessionRequest):
    """
    Create a Stripe Checkout Session

    Args:
        request: Request body containing checkout session parameters

    Returns:
        Stripe Checkout Session object
    """
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
        )
        return {"session_id": session.id, "url": session.url}
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating checkout session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@app.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    event = None

    if not STRIPE_WEBHOOK_SECRET or not sig_header:
        logger.warning("Webhook signature verification failed: missing secret or signature header")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Webhook signature verification failed"},
        )

    try:
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=sig_header, secret=STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"error": "Invalid payload"}
        )
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"error": "Invalid signature"}
        )

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        # Handle successful payment
        logger.info(f"Checkout session completed: {session.id}")
        # Add your business logic here
        # For example: update database, send confirmation email, etc.

    elif event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        # Handle successful payment
        logger.info(f"PaymentIntent was successful: {payment_intent.id}")
        # Add your business logic here

    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        # Handle failed payment
        logger.error(f"PaymentIntent failed: {payment_intent.id}")

    # ... handle other event types

    return {"status": "success"}


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy"}
