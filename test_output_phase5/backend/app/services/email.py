"""Email service wrapper."""

from typing import List, Dict, Any
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from pathlib import Path
import os

from app.core.config import settings

class EmailService:
    def __init__(self):
        # Mock config if variables not set
        self.conf = ConnectionConfig(
            MAIL_USERNAME=os.getenv("MAIL_USERNAME", "user"),
            MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", "password"),
            MAIL_FROM=os.getenv("MAIL_FROM", "test@example.com"),
            MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
            MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True
        )
        self.fastmail = FastMail(self.conf)

    async def send_email(
        self,
        subject: str,
        recipients: List[EmailStr],
        body: str,
        template_name: str = None
    ):
        """Send an email."""
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=body,
            subtype=MessageType.html
        )
        
        # await self.fastmail.send_message(message)
        print(f"Mock sending email to {recipients}: {subject}")

email_service = EmailService()
