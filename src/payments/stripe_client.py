"""
Stripe API Client

Production-ready Stripe integration for NexusAI.
"""

import os
import stripe
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class StripeError(Exception):
    """Base Stripe error."""
    
    def __init__(self, message: str, code: Optional[str] = None, param: Optional[str] = None):
        self.message = message
        self.code = code
        self.param = param
        super().__init__(message)


class PaymentError(StripeError):
    """Payment-related errors."""
    pass


class SubscriptionError(StripeError):
    """Subscription-related errors."""
    pass


class CustomerError(StripeError):
    """Customer-related errors."""
    pass


@dataclass
class StripeCustomer:
    """Stripe customer data."""
    id: str
    email: str
    name: Optional[str]
    created: datetime
    default_payment_method: Optional[str]
    metadata: Dict[str, str]


@dataclass
class StripeSubscription:
    """Stripe subscription data."""
    id: str
    customer_id: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    price_id: str
    product_id: str
    metadata: Dict[str, str]


@dataclass
class StripeInvoice:
    """Stripe invoice data."""
    id: str
    customer_id: str
    subscription_id: Optional[str]
    amount_due: int
    amount_paid: int
    currency: str
    status: str
    created: datetime
    invoice_pdf: Optional[str]
    hosted_invoice_url: Optional[str]


@dataclass
class StripePaymentIntent:
    """Stripe payment intent data."""
    id: str
    amount: int
    currency: str
    status: str
    client_secret: str
    customer_id: Optional[str]
    payment_method_id: Optional[str]


class StripeClient:
    """
    Production-ready Stripe API client.
    
    Handles all Stripe operations including customers, subscriptions,
    payments, and invoices.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        webhook_secret: Optional[str] = None,
    ):
        """
        Initialize Stripe client.
        
        Args:
            api_key: Stripe API key (defaults to STRIPE_API_KEY env var)
            webhook_secret: Webhook signing secret (defaults to STRIPE_WEBHOOK_SECRET env var)
        """
        self.api_key = api_key or os.getenv("STRIPE_API_KEY")
        self.webhook_secret = webhook_secret or os.getenv("STRIPE_WEBHOOK_SECRET")
        
        if self.api_key:
            stripe.api_key = self.api_key
        
        # Configure Stripe
        stripe.max_network_retries = 3
    
    def _handle_stripe_error(self, e: stripe.StripeError) -> None:
        """Convert Stripe errors to our custom errors."""
        error_code = getattr(e, 'code', None)
        param = getattr(e, 'param', None)
        message = str(e)
        
        if isinstance(e, stripe.CardError):
            raise PaymentError(message, error_code, param)
        elif isinstance(e, stripe.InvalidRequestError):
            if 'customer' in message.lower():
                raise CustomerError(message, error_code, param)
            elif 'subscription' in message.lower():
                raise SubscriptionError(message, error_code, param)
            raise StripeError(message, error_code, param)
        elif isinstance(e, stripe.AuthenticationError):
            raise StripeError("Invalid Stripe API key", "authentication_error")
        elif isinstance(e, stripe.RateLimitError):
            raise StripeError("Too many requests to Stripe", "rate_limit")
        else:
            raise StripeError(message, error_code, param)
    
    # ==================== Customer Operations ====================
    
    def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        payment_method_id: Optional[str] = None,
    ) -> StripeCustomer:
        """
        Create a new Stripe customer.
        
        Args:
            email: Customer email
            name: Customer name
            metadata: Additional metadata (e.g., user_id)
            payment_method_id: Default payment method to attach
            
        Returns:
            StripeCustomer object
        """
        try:
            params: Dict[str, Any] = {
                "email": email,
                "metadata": metadata or {},
            }
            
            if name:
                params["name"] = name
            
            if payment_method_id:
                params["payment_method"] = payment_method_id
                params["invoice_settings"] = {
                    "default_payment_method": payment_method_id
                }
            
            customer = stripe.Customer.create(**params)
            
            logger.info(f"Created Stripe customer: {customer.id} for {email}")
            
            return StripeCustomer(
                id=customer.id,
                email=customer.email,
                name=customer.name,
                created=datetime.fromtimestamp(customer.created),
                default_payment_method=customer.invoice_settings.default_payment_method if customer.invoice_settings else None,
                metadata=dict(customer.metadata) if customer.metadata else {},
            )
            
        except stripe.StripeError as e:
            logger.error(f"Failed to create customer: {e}")
            self._handle_stripe_error(e)
    
    def get_customer(self, customer_id: str) -> StripeCustomer:
        """
        Get a Stripe customer by ID.
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            StripeCustomer object
        """
        try:
            customer = stripe.Customer.retrieve(customer_id)
            
            return StripeCustomer(
                id=customer.id,
                email=customer.email,
                name=customer.name,
                created=datetime.fromtimestamp(customer.created),
                default_payment_method=customer.invoice_settings.default_payment_method if customer.invoice_settings else None,
                metadata=dict(customer.metadata) if customer.metadata else {},
            )
            
        except stripe.StripeError as e:
            logger.error(f"Failed to get customer {customer_id}: {e}")
            self._handle_stripe_error(e)
    
    def update_customer(
        self,
        customer_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        default_payment_method: Optional[str] = None,
    ) -> StripeCustomer:
        """
        Update a Stripe customer.
        
        Args:
            customer_id: Stripe customer ID
            email: New email
            name: New name
            metadata: New metadata (merged with existing)
            default_payment_method: New default payment method
            
        Returns:
            Updated StripeCustomer object
        """
        try:
            params: Dict[str, Any] = {}
            
            if email:
                params["email"] = email
            if name:
                params["name"] = name
            if metadata:
                params["metadata"] = metadata
            if default_payment_method:
                params["invoice_settings"] = {
                    "default_payment_method": default_payment_method
                }
            
            customer = stripe.Customer.modify(customer_id, **params)
            
            logger.info(f"Updated Stripe customer: {customer_id}")
            
            return StripeCustomer(
                id=customer.id,
                email=customer.email,
                name=customer.name,
                created=datetime.fromtimestamp(customer.created),
                default_payment_method=customer.invoice_settings.default_payment_method if customer.invoice_settings else None,
                metadata=dict(customer.metadata) if customer.metadata else {},
            )
            
        except stripe.StripeError as e:
            logger.error(f"Failed to update customer {customer_id}: {e}")
            self._handle_stripe_error(e)
    
    def delete_customer(self, customer_id: str) -> bool:
        """
        Delete a Stripe customer.
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            True if deleted successfully
        """
        try:
            stripe.Customer.delete(customer_id)
            logger.info(f"Deleted Stripe customer: {customer_id}")
            return True
            
        except stripe.StripeError as e:
            logger.error(f"Failed to delete customer {customer_id}: {e}")
            self._handle_stripe_error(e)
    
    # ==================== Subscription Operations ====================
    
    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None,
        payment_behavior: str = "default_incomplete",
    ) -> StripeSubscription:
        """
        Create a new subscription.
        
        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID
            trial_days: Number of trial days
            metadata: Additional metadata
            payment_behavior: How to handle payment collection
            
        Returns:
            StripeSubscription object
        """
        try:
            params: Dict[str, Any] = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "payment_behavior": payment_behavior,
                "metadata": metadata or {},
                "expand": ["latest_invoice.payment_intent"],
            }
            
            if trial_days:
                params["trial_period_days"] = trial_days
            
            subscription = stripe.Subscription.create(**params)
            
            logger.info(f"Created subscription {subscription.id} for customer {customer_id}")
            
            return self._parse_subscription(subscription)
            
        except stripe.StripeError as e:
            logger.error(f"Failed to create subscription: {e}")
            self._handle_stripe_error(e)
    
    def get_subscription(self, subscription_id: str) -> StripeSubscription:
        """
        Get a subscription by ID.
        
        Args:
            subscription_id: Stripe subscription ID
            
        Returns:
            StripeSubscription object
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return self._parse_subscription(subscription)
            
        except stripe.StripeError as e:
            logger.error(f"Failed to get subscription {subscription_id}: {e}")
            self._handle_stripe_error(e)
    
    def update_subscription(
        self,
        subscription_id: str,
        price_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        cancel_at_period_end: Optional[bool] = None,
        proration_behavior: str = "create_prorations",
    ) -> StripeSubscription:
        """
        Update a subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            price_id: New price ID (for plan changes)
            metadata: New metadata
            cancel_at_period_end: Whether to cancel at period end
            proration_behavior: How to handle prorations
            
        Returns:
            Updated StripeSubscription object
        """
        try:
            params: Dict[str, Any] = {}
            
            if price_id:
                # Get current subscription to find the item ID
                current = stripe.Subscription.retrieve(subscription_id)
                item_id = current["items"]["data"][0].id
                params["items"] = [{"id": item_id, "price": price_id}]
                params["proration_behavior"] = proration_behavior
            
            if metadata:
                params["metadata"] = metadata
            
            if cancel_at_period_end is not None:
                params["cancel_at_period_end"] = cancel_at_period_end
            
            subscription = stripe.Subscription.modify(subscription_id, **params)
            
            logger.info(f"Updated subscription: {subscription_id}")
            
            return self._parse_subscription(subscription)
            
        except stripe.StripeError as e:
            logger.error(f"Failed to update subscription {subscription_id}: {e}")
            self._handle_stripe_error(e)
    
    def cancel_subscription(
        self,
        subscription_id: str,
        immediately: bool = False,
    ) -> StripeSubscription:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            immediately: If True, cancel immediately; otherwise cancel at period end
            
        Returns:
            Cancelled StripeSubscription object
        """
        try:
            if immediately:
                subscription = stripe.Subscription.delete(subscription_id)
            else:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            
            logger.info(f"Cancelled subscription: {subscription_id} (immediately={immediately})")
            
            return self._parse_subscription(subscription)
            
        except stripe.StripeError as e:
            logger.error(f"Failed to cancel subscription {subscription_id}: {e}")
            self._handle_stripe_error(e)
    
    def list_subscriptions(
        self,
        customer_id: str,
        status: Optional[str] = None,
        limit: int = 10,
    ) -> List[StripeSubscription]:
        """
        List subscriptions for a customer.
        
        Args:
            customer_id: Stripe customer ID
            status: Filter by status (active, canceled, etc.)
            limit: Maximum number of results
            
        Returns:
            List of StripeSubscription objects
        """
        try:
            params: Dict[str, Any] = {
                "customer": customer_id,
                "limit": limit,
            }
            
            if status:
                params["status"] = status
            
            subscriptions = stripe.Subscription.list(**params)
            
            return [self._parse_subscription(sub) for sub in subscriptions.data]
            
        except stripe.StripeError as e:
            logger.error(f"Failed to list subscriptions for {customer_id}: {e}")
            self._handle_stripe_error(e)
    
    def _parse_subscription(self, subscription: stripe.Subscription) -> StripeSubscription:
        """Parse Stripe subscription object."""
        item = subscription["items"]["data"][0]
        
        return StripeSubscription(
            id=subscription.id,
            customer_id=subscription.customer,
            status=subscription.status,
            current_period_start=datetime.fromtimestamp(subscription.current_period_start),
            current_period_end=datetime.fromtimestamp(subscription.current_period_end),
            cancel_at_period_end=subscription.cancel_at_period_end,
            price_id=item.price.id,
            product_id=item.price.product,
            metadata=dict(subscription.metadata) if subscription.metadata else {},
        )
    
    # ==================== Payment Operations ====================
    
    def create_payment_intent(
        self,
        amount: int,
        currency: str = "usd",
        customer_id: Optional[str] = None,
        payment_method_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        automatic_payment_methods: bool = True,
    ) -> StripePaymentIntent:
        """
        Create a payment intent for one-time payments.
        
        Args:
            amount: Amount in cents
            currency: Currency code
            customer_id: Stripe customer ID
            payment_method_id: Payment method to use
            metadata: Additional metadata
            automatic_payment_methods: Enable automatic payment methods
            
        Returns:
            StripePaymentIntent object
        """
        try:
            params: Dict[str, Any] = {
                "amount": amount,
                "currency": currency,
                "metadata": metadata or {},
            }
            
            if customer_id:
                params["customer"] = customer_id
            
            if payment_method_id:
                params["payment_method"] = payment_method_id
            
            if automatic_payment_methods:
                params["automatic_payment_methods"] = {"enabled": True}
            
            intent = stripe.PaymentIntent.create(**params)
            
            logger.info(f"Created payment intent: {intent.id} for {amount} {currency}")
            
            return StripePaymentIntent(
                id=intent.id,
                amount=intent.amount,
                currency=intent.currency,
                status=intent.status,
                client_secret=intent.client_secret,
                customer_id=intent.customer,
                payment_method_id=intent.payment_method,
            )
            
        except stripe.StripeError as e:
            logger.error(f"Failed to create payment intent: {e}")
            self._handle_stripe_error(e)
    
    def confirm_payment_intent(
        self,
        payment_intent_id: str,
        payment_method_id: Optional[str] = None,
    ) -> StripePaymentIntent:
        """
        Confirm a payment intent.
        
        Args:
            payment_intent_id: Payment intent ID
            payment_method_id: Payment method to use
            
        Returns:
            Confirmed StripePaymentIntent object
        """
        try:
            params: Dict[str, Any] = {}
            
            if payment_method_id:
                params["payment_method"] = payment_method_id
            
            intent = stripe.PaymentIntent.confirm(payment_intent_id, **params)
            
            logger.info(f"Confirmed payment intent: {payment_intent_id}")
            
            return StripePaymentIntent(
                id=intent.id,
                amount=intent.amount,
                currency=intent.currency,
                status=intent.status,
                client_secret=intent.client_secret,
                customer_id=intent.customer,
                payment_method_id=intent.payment_method,
            )
            
        except stripe.StripeError as e:
            logger.error(f"Failed to confirm payment intent {payment_intent_id}: {e}")
            self._handle_stripe_error(e)
    
    # ==================== Invoice Operations ====================
    
    def get_invoice(self, invoice_id: str) -> StripeInvoice:
        """
        Get an invoice by ID.
        
        Args:
            invoice_id: Stripe invoice ID
            
        Returns:
            StripeInvoice object
        """
        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            return self._parse_invoice(invoice)
            
        except stripe.StripeError as e:
            logger.error(f"Failed to get invoice {invoice_id}: {e}")
            self._handle_stripe_error(e)
    
    def list_invoices(
        self,
        customer_id: str,
        limit: int = 10,
        status: Optional[str] = None,
    ) -> List[StripeInvoice]:
        """
        List invoices for a customer.
        
        Args:
            customer_id: Stripe customer ID
            limit: Maximum number of results
            status: Filter by status (paid, open, etc.)
            
        Returns:
            List of StripeInvoice objects
        """
        try:
            params: Dict[str, Any] = {
                "customer": customer_id,
                "limit": limit,
            }
            
            if status:
                params["status"] = status
            
            invoices = stripe.Invoice.list(**params)
            
            return [self._parse_invoice(inv) for inv in invoices.data]
            
        except stripe.StripeError as e:
            logger.error(f"Failed to list invoices for {customer_id}: {e}")
            self._handle_stripe_error(e)
    
    def create_invoice(
        self,
        customer_id: str,
        auto_advance: bool = True,
        collection_method: str = "charge_automatically",
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> StripeInvoice:
        """
        Create a new invoice.
        
        Args:
            customer_id: Stripe customer ID
            auto_advance: Auto-finalize the invoice
            collection_method: How to collect payment
            description: Invoice description
            metadata: Additional metadata
            
        Returns:
            StripeInvoice object
        """
        try:
            params: Dict[str, Any] = {
                "customer": customer_id,
                "auto_advance": auto_advance,
                "collection_method": collection_method,
                "metadata": metadata or {},
            }
            
            if description:
                params["description"] = description
            
            invoice = stripe.Invoice.create(**params)
            
            logger.info(f"Created invoice {invoice.id} for customer {customer_id}")
            
            return self._parse_invoice(invoice)
            
        except stripe.StripeError as e:
            logger.error(f"Failed to create invoice: {e}")
            self._handle_stripe_error(e)
    
    def finalize_invoice(self, invoice_id: str) -> StripeInvoice:
        """
        Finalize a draft invoice.
        
        Args:
            invoice_id: Stripe invoice ID
            
        Returns:
            Finalized StripeInvoice object
        """
        try:
            invoice = stripe.Invoice.finalize_invoice(invoice_id)
            logger.info(f"Finalized invoice: {invoice_id}")
            return self._parse_invoice(invoice)
            
        except stripe.StripeError as e:
            logger.error(f"Failed to finalize invoice {invoice_id}: {e}")
            self._handle_stripe_error(e)
    
    def pay_invoice(self, invoice_id: str) -> StripeInvoice:
        """
        Pay an invoice.
        
        Args:
            invoice_id: Stripe invoice ID
            
        Returns:
            Paid StripeInvoice object
        """
        try:
            invoice = stripe.Invoice.pay(invoice_id)
            logger.info(f"Paid invoice: {invoice_id}")
            return self._parse_invoice(invoice)
            
        except stripe.StripeError as e:
            logger.error(f"Failed to pay invoice {invoice_id}: {e}")
            self._handle_stripe_error(e)
    
    def _parse_invoice(self, invoice: stripe.Invoice) -> StripeInvoice:
        """Parse Stripe invoice object."""
        return StripeInvoice(
            id=invoice.id,
            customer_id=invoice.customer,
            subscription_id=invoice.subscription,
            amount_due=invoice.amount_due,
            amount_paid=invoice.amount_paid,
            currency=invoice.currency,
            status=invoice.status,
            created=datetime.fromtimestamp(invoice.created),
            invoice_pdf=invoice.invoice_pdf,
            hosted_invoice_url=invoice.hosted_invoice_url,
        )
    
    # ==================== Payment Method Operations ====================
    
    def attach_payment_method(
        self,
        payment_method_id: str,
        customer_id: str,
    ) -> Dict[str, Any]:
        """
        Attach a payment method to a customer.
        
        Args:
            payment_method_id: Stripe payment method ID
            customer_id: Stripe customer ID
            
        Returns:
            Payment method details
        """
        try:
            payment_method = stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id,
            )
            
            logger.info(f"Attached payment method {payment_method_id} to customer {customer_id}")
            
            return {
                "id": payment_method.id,
                "type": payment_method.type,
                "card": {
                    "brand": payment_method.card.brand,
                    "last4": payment_method.card.last4,
                    "exp_month": payment_method.card.exp_month,
                    "exp_year": payment_method.card.exp_year,
                } if payment_method.card else None,
            }
            
        except stripe.StripeError as e:
            logger.error(f"Failed to attach payment method: {e}")
            self._handle_stripe_error(e)
    
    def detach_payment_method(self, payment_method_id: str) -> bool:
        """
        Detach a payment method from its customer.
        
        Args:
            payment_method_id: Stripe payment method ID
            
        Returns:
            True if detached successfully
        """
        try:
            stripe.PaymentMethod.detach(payment_method_id)
            logger.info(f"Detached payment method: {payment_method_id}")
            return True
            
        except stripe.StripeError as e:
            logger.error(f"Failed to detach payment method {payment_method_id}: {e}")
            self._handle_stripe_error(e)
    
    def list_payment_methods(
        self,
        customer_id: str,
        type: str = "card",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        List payment methods for a customer.
        
        Args:
            customer_id: Stripe customer ID
            type: Payment method type (card, bank_account, etc.)
            limit: Maximum number of results
            
        Returns:
            List of payment method details
        """
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type=type,
                limit=limit,
            )
            
            return [
                {
                    "id": pm.id,
                    "type": pm.type,
                    "card": {
                        "brand": pm.card.brand,
                        "last4": pm.card.last4,
                        "exp_month": pm.card.exp_month,
                        "exp_year": pm.card.exp_year,
                    } if pm.card else None,
                }
                for pm in payment_methods.data
            ]
            
        except stripe.StripeError as e:
            logger.error(f"Failed to list payment methods for {customer_id}: {e}")
            self._handle_stripe_error(e)
    
    # ==================== Setup Intent (for saving cards) ====================
    
    def create_setup_intent(
        self,
        customer_id: str,
        payment_method_types: Optional[List[str]] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a setup intent for saving payment methods.
        
        Args:
            customer_id: Stripe customer ID
            payment_method_types: Allowed payment method types
            metadata: Additional metadata
            
        Returns:
            Setup intent details including client_secret
        """
        try:
            params: Dict[str, Any] = {
                "customer": customer_id,
                "metadata": metadata or {},
            }
            
            if payment_method_types:
                params["payment_method_types"] = payment_method_types
            else:
                params["automatic_payment_methods"] = {"enabled": True}
            
            setup_intent = stripe.SetupIntent.create(**params)
            
            logger.info(f"Created setup intent {setup_intent.id} for customer {customer_id}")
            
            return {
                "id": setup_intent.id,
                "client_secret": setup_intent.client_secret,
                "status": setup_intent.status,
            }
            
        except stripe.StripeError as e:
            logger.error(f"Failed to create setup intent: {e}")
            self._handle_stripe_error(e)
    
    # ==================== Checkout Session ====================
    
    def create_checkout_session(
        self,
        price_id: str,
        success_url: str,
        cancel_url: str,
        customer_id: Optional[str] = None,
        customer_email: Optional[str] = None,
        mode: str = "subscription",
        trial_days: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None,
        allow_promotion_codes: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout session.
        
        Args:
            price_id: Stripe price ID
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancel
            customer_id: Existing customer ID
            customer_email: Email for new customer
            mode: Session mode (subscription, payment, setup)
            trial_days: Trial period for subscriptions
            metadata: Additional metadata
            allow_promotion_codes: Allow promo codes
            
        Returns:
            Checkout session details including URL
        """
        try:
            params: Dict[str, Any] = {
                "line_items": [{"price": price_id, "quantity": 1}],
                "mode": mode,
                "success_url": success_url,
                "cancel_url": cancel_url,
                "allow_promotion_codes": allow_promotion_codes,
                "metadata": metadata or {},
            }
            
            if customer_id:
                params["customer"] = customer_id
            elif customer_email:
                params["customer_email"] = customer_email
            
            if trial_days and mode == "subscription":
                params["subscription_data"] = {"trial_period_days": trial_days}
            
            session = stripe.checkout.Session.create(**params)
            
            logger.info(f"Created checkout session: {session.id}")
            
            return {
                "id": session.id,
                "url": session.url,
                "customer_id": session.customer,
                "subscription_id": session.subscription,
            }
            
        except stripe.StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            self._handle_stripe_error(e)
    
    # ==================== Portal Session ====================
    
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
            Portal session details including URL
        """
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            
            logger.info(f"Created portal session for customer {customer_id}")
            
            return {
                "id": session.id,
                "url": session.url,
            }
            
        except stripe.StripeError as e:
            logger.error(f"Failed to create portal session: {e}")
            self._handle_stripe_error(e)
    
    # ==================== Webhook Verification ====================
    
    def verify_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> stripe.Event:
        """
        Verify and construct a webhook event.
        
        Args:
            payload: Raw request body
            signature: Stripe-Signature header
            
        Returns:
            Verified Stripe event
            
        Raises:
            StripeError: If verification fails
        """
        if not self.webhook_secret:
            raise StripeError("Webhook secret not configured")
        
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret,
            )
            return event
            
        except stripe.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise StripeError("Invalid webhook signature", "signature_invalid")
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            raise StripeError("Invalid webhook payload", "payload_invalid")
