"""
Valeric Email Module

Provides transactional email functionality via Resend.com.
"""

from src.emails.client import (
    EmailAttachment,
    EmailClient,
    EmailResult,
    get_email_client,
    send_app_generation_complete_email,
    send_password_reset_email,
    send_payment_confirmation_email,
    send_verification_email,
    send_welcome_email,
)

__all__ = [
    "EmailClient",
    "EmailResult",
    "EmailAttachment",
    "get_email_client",
    "send_verification_email",
    "send_welcome_email",
    "send_password_reset_email",
    "send_payment_confirmation_email",
    "send_app_generation_complete_email",
]
