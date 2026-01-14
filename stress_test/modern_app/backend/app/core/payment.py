import logging
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from stripe import Checkout, Stripe, Webhook

# Initialize FastAPI app
app = FastAPI(
    title="Stripe Checkout API",
    description="API for Stripe checkout sessions and webhook handling",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Stripe
stripe_api_key = os.getenv("STRIPE_SECRET_KEY")
if not stripe_api_key:
    raise ValueError("STRIPE_SECRET_KEY environment variable not set")

Stripe.api_key = stripe_api_key
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProductItem(BaseModel):
    price_id: str
    quantity: int


class CheckoutSessionRequest(BaseModel):
    customer_email: Optional[str] = None
    success_url: str
    cancel_url: str
    mode: str = "payment"
    line_items: list[ProductItem]


@app.post("/create-checkout-session")
async def create_checkout_session(request: CheckoutSessionRequest):
    """
    Create a Stripe Checkout Session

    Args:
        request: CheckoutSessionRequest containing:
            - customer_email: Optional customer email
            - success_url: URL to redirect to on success
            - cancel_url: URL to redirect to on cancel
            - mode: Checkout mode (payment, subscription, etc.)
            - line_items: List of product items with price_id and quantity

    Returns:
        JSON response with session ID or error
    """
    try:
        session = Checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": item.price_id,
                    "quantity": item.quantity,
                }
                for item in request.line_items
            ],
            mode=request.mode,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            customer_email=request.customer_email,
        )

        return {"sessionId": session.id}

    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session",
        )


@app.post("/webhook")
async def webhook_receiver(request: Request):
    """
    Handle Stripe webhook events

    Args:
        request: FastAPI Request object

    Returns:
        JSON response with success or error
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header or not endpoint_secret:
        logger.error("Missing stripe-signature header or webhook secret")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header or webhook secret",
        )

    try:
        event = Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook signature verification failed"
        )

    # Handle the event
    try:
        if event.type == "checkout.session.completed":
            session = event.data.object
            logger.info(f"Checkout session completed: {session.id}")

            # Here you would typically update your database
            # or send a confirmation email, etc.

        elif event.type == "payment_intent.succeeded":
            intent = event.data.object
            logger.info(f"Payment succeeded: {intent.id}")

        elif event.type == "payment_method.attached":
            payment_method = event.data.object
            logger.info(f"Payment method attached: {payment_method.id}")

        # ... handle other event types

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error processing webhook event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing webhook event",
        )


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
