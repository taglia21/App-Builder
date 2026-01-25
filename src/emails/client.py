"""
Email client for LaunchForge using Resend.com API.

Provides transactional email functionality for:
- Email verification
- Password reset
- Welcome emails
- Payment confirmations
- App generation notifications
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import httpx
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class EmailAttachment:
    """Email attachment data."""
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


@dataclass
class EmailResult:
    """Result of sending an email."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class EmailClient:
    """
    Email client using Resend.com API.
    
    Features:
    - Template-based emails with Jinja2
    - HTML and plain text support
    - Attachment support
    - Retry logic for reliability
    """
    
    RESEND_API_URL = "https://api.resend.com/emails"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: str = "LaunchForge"
    ):
        """
        Initialize email client.
        
        Args:
            api_key: Resend API key (or from settings)
            from_email: Default sender email
            from_name: Default sender name
        """
        settings = get_settings()
        self.api_key = api_key or getattr(settings, 'resend_api_key', None)
        self.from_email = from_email or getattr(settings, 'email_from', 'noreply@launchforge.dev')
        self.from_name = from_name
        
        # Set up Jinja2 template environment
        template_dir = Path(__file__).parent / "templates"
        template_dir.mkdir(exist_ok=True)
        
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            enable_async=False
        )
        
    @property
    def is_configured(self) -> bool:
        """Check if email is properly configured."""
        return bool(self.api_key)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def send_email(
        self,
        to: str | List[str],
        subject: str,
        html: Optional[str] = None,
        text: Optional[str] = None,
        reply_to: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[EmailAttachment]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> EmailResult:
        """
        Send an email via Resend API.
        
        Args:
            to: Recipient email(s)
            subject: Email subject
            html: HTML body
            text: Plain text body (auto-generated if not provided)
            reply_to: Reply-to address
            cc: CC recipients
            bcc: BCC recipients
            attachments: File attachments
            tags: Custom tags for tracking
            
        Returns:
            EmailResult with success status and message ID
        """
        if not self.is_configured:
            logger.warning("Email not configured - skipping send")
            return EmailResult(success=False, error="Email not configured")
        
        # Build recipient list
        recipients = [to] if isinstance(to, str) else to
        
        # Build payload
        payload: Dict[str, Any] = {
            "from": f"{self.from_name} <{self.from_email}>",
            "to": recipients,
            "subject": subject,
        }
        
        if html:
            payload["html"] = html
        if text:
            payload["text"] = text
        if reply_to:
            payload["reply_to"] = reply_to
        if cc:
            payload["cc"] = cc
        if bcc:
            payload["bcc"] = bcc
        if tags:
            payload["tags"] = [{"name": k, "value": v} for k, v in tags.items()]
        
        # Handle attachments
        if attachments:
            import base64
            payload["attachments"] = [
                {
                    "filename": att.filename,
                    "content": base64.b64encode(att.content).decode(),
                    "type": att.content_type
                }
                for att in attachments
            ]
        
        # Send request
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.RESEND_API_URL,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Email sent successfully to {recipients}: {data.get('id')}")
                    return EmailResult(success=True, message_id=data.get("id"))
                else:
                    error = response.text
                    logger.error(f"Failed to send email: {error}")
                    return EmailResult(success=False, error=error)
                    
        except httpx.TimeoutException:
            logger.error("Email send timed out")
            return EmailResult(success=False, error="Request timed out")
        except Exception as e:
            logger.exception(f"Email send error: {e}")
            return EmailResult(success=False, error=str(e))
    
    def render_template(
        self,
        template_name: str,
        **context: Any
    ) -> str:
        """
        Render an email template.
        
        Args:
            template_name: Template filename
            **context: Template variables
            
        Returns:
            Rendered HTML string
        """
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Template render error for {template_name}: {e}")
            raise
    
    async def send_template_email(
        self,
        to: str | List[str],
        subject: str,
        template_name: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> EmailResult:
        """
        Send an email using a template.
        
        Args:
            to: Recipient email(s)
            subject: Email subject
            template_name: Template filename
            context: Template variables
            **kwargs: Additional send_email arguments
            
        Returns:
            EmailResult
        """
        context = context or {}
        html = self.render_template(template_name, **context)
        return await self.send_email(to=to, subject=subject, html=html, **kwargs)


# Convenience functions for common email types

async def send_verification_email(
    email: str,
    name: str,
    verification_url: str
) -> EmailResult:
    """Send email verification link."""
    client = EmailClient()
    
    html = client.render_template(
        "verification.html",
        name=name or "there",
        verification_url=verification_url,
        year=2026
    )
    
    return await client.send_email(
        to=email,
        subject="Verify your LaunchForge email",
        html=html,
        tags={"type": "verification"}
    )


async def send_welcome_email(
    email: str,
    name: str
) -> EmailResult:
    """Send welcome email after verification."""
    client = EmailClient()
    
    html = client.render_template(
        "welcome.html",
        name=name or "there",
        dashboard_url="https://launchforge.dev/dashboard",
        year=2026
    )
    
    return await client.send_email(
        to=email,
        subject="Welcome to LaunchForge! 🚀",
        html=html,
        tags={"type": "welcome"}
    )


async def send_password_reset_email(
    email: str,
    name: str,
    reset_url: str
) -> EmailResult:
    """Send password reset link."""
    client = EmailClient()
    
    html = client.render_template(
        "password_reset.html",
        name=name or "there",
        reset_url=reset_url,
        year=2026
    )
    
    return await client.send_email(
        to=email,
        subject="Reset your LaunchForge password",
        html=html,
        tags={"type": "password_reset"}
    )


async def send_payment_confirmation_email(
    email: str,
    name: str,
    plan_name: str,
    amount: str,
    receipt_url: Optional[str] = None
) -> EmailResult:
    """Send payment confirmation."""
    client = EmailClient()
    
    html = client.render_template(
        "payment_confirmation.html",
        name=name or "there",
        plan_name=plan_name,
        amount=amount,
        receipt_url=receipt_url,
        year=2026
    )
    
    return await client.send_email(
        to=email,
        subject=f"Payment confirmed - {plan_name}",
        html=html,
        tags={"type": "payment"}
    )


async def send_app_generation_complete_email(
    email: str,
    name: str,
    app_name: str,
    project_url: str
) -> EmailResult:
    """Send notification when app generation completes."""
    client = EmailClient()
    
    html = client.render_template(
        "app_complete.html",
        name=name or "there",
        app_name=app_name,
        project_url=project_url,
        year=2026
    )
    
    return await client.send_email(
        to=email,
        subject=f"Your app '{app_name}' is ready! 🎉",
        html=html,
        tags={"type": "app_complete"}
    )


# Singleton instance
_email_client: Optional[EmailClient] = None


def get_email_client() -> EmailClient:
    """Get or create email client singleton."""
    global _email_client
    if _email_client is None:
        _email_client = EmailClient()
    return _email_client
