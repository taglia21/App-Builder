import logging
from typing import Optional

import stripe
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Stripe Payment API",
    description="API for handling Stripe payments",
    version="1.0.0",
)

# Configure Stripe
stripe.api_key = "your_stripe_secret_key"  # Replace with your actual Stripe secret key
webhook_secret = "your_webhook_signing_secret"  # Replace with your actual webhook signing secret


class CheckoutSessionRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str
    quantity: Optional[int] = 1
    customer_email: Optional[str] = None
    metadata: Optional[dict] = None


@app.post("/create-checkout-session")
async def create_checkout_session(request: CheckoutSessionRequest):
    """
    Create a Stripe Checkout Session

    Args:
        request: CheckoutSessionRequest with required parameters

    Returns:
        JSON response with session ID or error
    """
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": request.price_id,
                    "quantity": request.quantity,
                }
            ],
            mode="payment",
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            customer_email=request.customer_email,
            metadata=request.metadata or {},
        )

        return JSONResponse(status_code=status.HTTP_200_OK, content={"sessionId": session.id})

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@app.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events

    Args:
        request: FastAPI Request object

    Returns:
        JSON response with success status
    """
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    if not sig_header:
        logger.error("No Stripe-Signature header found")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Stripe-Signature header"
        )

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        # Handle successful checkout session here
        logger.info(f"Checkout session completed: {session.id}")

    elif event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        # Handle successful payment here
        logger.info(f"Payment succeeded: {payment_intent.id}")

    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        # Handle failed payment here
        logger.error(f"Payment failed: {payment_intent.id}")

    # Add more event types as needed

    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "success"})


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy"}
