
"""Email service for sending transactional emails."""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class EmailBackend(ABC):
    """Abstract base class for email backends."""
    
    @abstractmethod
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
    ) -> bool:
        pass


class SendGridBackend(EmailBackend):
    """SendGrid email backend."""
    
    def __init__(self, api_key: str, from_email: str, from_name: str):
        self.api_key = api_key
        self.default_from_email = from_email
        self.default_from_name = from_name
    
    async def send_email(
        self, to_email: str, subject: str, html_content: str,
        text_content: Optional[str] = None, from_email: Optional[str] = None,
        from_name: Optional[str] = None,
    ) -> bool:
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, Email, To, Content
            sg = sendgrid.SendGridAPIClient(api_key=self.api_key)
            from_addr = Email(from_email or self.default_from_email, from_name or self.default_from_name)
            message = Mail(from_email=from_addr, to_emails=To(to_email), subject=subject, html_content=html_content)
            if text_content:
                message.add_content(Content("text/plain", text_content))
            response = sg.send(message)
            return response.status_code in (200, 201, 202)
        except ImportError:
            logger.error("SendGrid not installed. Run: pip install sendgrid")
            return False
        except Exception as e:
            logger.error(f"SendGrid error: {e}")
            return False


class SMTPBackend(EmailBackend):
    """SMTP email backend."""
    
    def __init__(self, host: str, port: int, username: str, password: str,
                 use_tls: bool, from_email: str, from_name: str):
        self.host, self.port = host, port
        self.username, self.password = username, password
        self.use_tls = use_tls
        self.default_from_email = from_email
        self.default_from_name = from_name
    
    async def send_email(
        self, to_email: str, subject: str, html_content: str,
        text_content: Optional[str] = None, from_email: Optional[str] = None,
        from_name: Optional[str] = None,
    ) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{from_name or self.default_from_name} <{from_email or self.default_from_email}>"
            msg["To"] = to_email
            if text_content: msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))
            with smtplib.SMTP(self.host, self.port) as server:
                if self.use_tls: server.starttls()
                server.login(self.username, self.password)
                server.sendmail(from_email or self.default_from_email, to_email, msg.as_string())
            return True
        except Exception as e:
            logger.error(f"SMTP error: {e}")
            return False


class LogOnlyBackend(EmailBackend):
    """Development backend that only logs emails."""
    async def send_email(self, to_email: str, subject: str, html_content: str,
                         text_content: Optional[str] = None, from_email: Optional[str] = None,
                         from_name: Optional[str] = None) -> bool:
        logger.info(f"[DEV EMAIL] To: {to_email}, Subject: {subject}")
        return True


class EmailService:
    """Main email service with template support."""
    
    def __init__(self, backend: EmailBackend):
        self.backend = backend
    
    @classmethod
    def from_settings(cls, settings) -> "EmailService":
        if settings.SENDGRID_API_KEY:
            backend = SendGridBackend(settings.SENDGRID_API_KEY, settings.EMAIL_FROM_ADDRESS, settings.EMAIL_FROM_NAME)
        elif settings.SMTP_HOST:
            backend = SMTPBackend(settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_USER or "",
                                  settings.SMTP_PASSWORD or "", settings.SMTP_USE_TLS,
                                  settings.EMAIL_FROM_ADDRESS, settings.EMAIL_FROM_NAME)
        else:
            logger.warning("No email backend configured, using log-only backend")
            backend = LogOnlyBackend()
        return cls(backend)
    
    async def send_welcome_email(self, to_email: str, user_name: str) -> bool:
        return await self.backend.send_email(to_email, "Welcome to App-Builder!",
            f"<h1>Welcome, {user_name}!</h1><p>Thank you for signing up.</p>")
    
    async def send_trial_ending_email(self, to_email: str, days: int, url: str) -> bool:
        return await self.backend.send_email(to_email, f"Your trial ends in {days} days",
            f"<h1>Trial Ending</h1><p>Upgrade at: <a href="{url}">{url}</a></p>")
    
    async def send_payment_failed_email(self, to_email: str, url: str) -> bool:
        return await self.backend.send_email(to_email, "Action Required: Payment Failed",
            f"<h1>Payment Failed</h1><p>Update payment: <a href="{url}">{url}</a></p>")
    
    async def send_subscription_confirmed_email(self, to_email: str, plan: str) -> bool:
        return await self.backend.send_email(to_email, f"Subscription Confirmed: {plan}",
            f"<h1>Subscription Confirmed!</h1><p>You are now on the {plan} plan.</p>")
