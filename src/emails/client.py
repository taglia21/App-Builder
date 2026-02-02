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
import time
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound

from src.config import get_settings

logger = logging.getLogger(__name__)


class EmailError(Exception):
    """Base exception for email errors."""
    pass


class EmailConfigurationError(EmailError):
    """Raised when email is not properly configured."""
    pass


class EmailSendError(EmailError):
    """Raised when email sending fails."""
    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class EmailTemplateError(EmailError):
    """Raised when email template rendering fails."""
    pass


class EmailRateLimitError(EmailError):
    """Raised when rate limited by email provider."""
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after


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
    error_code: Optional[str] = None
    duration_ms: Optional[float] = None


class EmailClient:
    """
    Email client using Resend.com API.
    
    Features:
    - Template-based emails with Jinja2
    - HTML and plain text support
    - Attachment support
    - Retry logic for reliability
    - Comprehensive error handling
    - Metrics tracking
    """
    
    RESEND_API_URL = "https://api.resend.com/emails"
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds
    
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
        
        Raises:
            EmailConfigurationError: If required settings are missing
        """
        settings = get_settings()
        self.api_key = api_key or getattr(settings, 'resend_api_key', None)
        self.from_email = from_email or getattr(settings, 'email_from', 'noreply@nexusai.dev')
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
    
    def validate_configuration(self) -> None:
        """
        Validate email configuration.
        
        Raises:
            EmailConfigurationError: If configuration is invalid
        """
        if not self.api_key:
            raise EmailConfigurationError(
                "RESEND_API_KEY not configured. "
                "Please set RESEND_API_KEY environment variable."
            )
        if not self.from_email:
            raise EmailConfigurationError(
                "FROM_EMAIL not configured. "
                "Please set FROM_EMAIL environment variable."
            )
    
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
        tags: Optional[Dict[str, str]] = None,
        raise_on_error: bool = False
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
            raise_on_error: Whether to raise exceptions on failure
            
        Returns:
            EmailResult with success status and message ID
            
        Raises:
            EmailConfigurationError: If email not configured (when raise_on_error=True)
            EmailSendError: If sending fails (when raise_on_error=True)
            EmailRateLimitError: If rate limited (when raise_on_error=True)
        """
        start_time = time.time()
        
        # Import metrics for tracking
        try:
            from src.monitoring.metrics import track_email_send
        except ImportError:
            track_email_send = None
        
        template_name = tags.get("type", "unknown") if tags else "unknown"
        
        if not self.is_configured:
            error_msg = "Email not configured - RESEND_API_KEY missing"
            logger.warning(error_msg)
            if raise_on_error:
                raise EmailConfigurationError(error_msg)
            return EmailResult(success=False, error=error_msg, error_code="NOT_CONFIGURED")
        
        # Build recipient list
        recipients = [to] if isinstance(to, str) else to
        
        # Validate recipients
        if not recipients:
            error_msg = "No recipients specified"
            if raise_on_error:
                raise EmailSendError(error_msg)
            return EmailResult(success=False, error=error_msg, error_code="NO_RECIPIENTS")
        
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
        
        # Send request with retry logic
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.RESEND_API_URL,
                        headers=self._get_headers(),
                        json=payload,
                        timeout=30.0
                    )
                    
                    duration_ms = (time.time() - start_time) * 1000
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"Email sent successfully to {recipients}: {data.get('id')}")
                        
                        # Track success
                        if track_email_send:
                            track_email_send(template_name, True, duration_ms / 1000)
                        
                        return EmailResult(
                            success=True, 
                            message_id=data.get("id"),
                            duration_ms=duration_ms
                        )
                    
                    elif response.status_code == 429:
                        # Rate limited
                        retry_after = int(response.headers.get("Retry-After", 60))
                        error_msg = f"Rate limited by Resend. Retry after {retry_after}s"
                        logger.warning(f"{error_msg} (attempt {attempt + 1}/{self.MAX_RETRIES})")
                        
                        if attempt < self.MAX_RETRIES - 1:
                            await self._async_sleep(min(retry_after, 5))
                            continue
                        
                        if raise_on_error:
                            raise EmailRateLimitError(error_msg, retry_after=retry_after)
                        return EmailResult(
                            success=False, 
                            error=error_msg, 
                            error_code="RATE_LIMITED",
                            duration_ms=duration_ms
                        )
                    
                    elif response.status_code >= 500:
                        # Server error - retry
                        error_msg = f"Resend server error: {response.status_code}"
                        logger.warning(f"{error_msg} (attempt {attempt + 1}/{self.MAX_RETRIES})")
                        last_error = error_msg
                        
                        if attempt < self.MAX_RETRIES - 1:
                            await self._async_sleep(self.RETRY_DELAY * (attempt + 1))
                            continue
                    
                    else:
                        # Client error - don't retry
                        try:
                            error_data = response.json()
                            error_msg = error_data.get("message", response.text)
                        except (ConnectionError, TimeoutError, Exception) as e:
                            error_msg = response.text
                        
                        logger.error(f"Failed to send email: {response.status_code} - {error_msg}")
                        
                        # Track failure
                        if track_email_send:
                            track_email_send(template_name, False, duration_ms / 1000)
                        
                        if raise_on_error:
                            raise EmailSendError(
                                error_msg, 
                                status_code=response.status_code,
                                response_body=response.text
                            )
                        return EmailResult(
                            success=False, 
                            error=error_msg,
                            error_code=f"HTTP_{response.status_code}",
                            duration_ms=duration_ms
                        )
                        
            except httpx.TimeoutException as e:
                duration_ms = (time.time() - start_time) * 1000
                error_msg = f"Email send timed out after 30s"
                logger.warning(f"{error_msg} (attempt {attempt + 1}/{self.MAX_RETRIES})")
                last_error = error_msg
                
                if attempt < self.MAX_RETRIES - 1:
                    await self._async_sleep(self.RETRY_DELAY * (attempt + 1))
                    continue
                    
            except httpx.ConnectError as e:
                duration_ms = (time.time() - start_time) * 1000
                error_msg = f"Failed to connect to Resend API: {str(e)}"
                logger.warning(f"{error_msg} (attempt {attempt + 1}/{self.MAX_RETRIES})")
                last_error = error_msg
                
                if attempt < self.MAX_RETRIES - 1:
                    await self._async_sleep(self.RETRY_DELAY * (attempt + 1))
                    continue
                    
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                error_msg = f"Email send error: {str(e)}"
                logger.exception(error_msg)
                last_error = error_msg
                
                if attempt < self.MAX_RETRIES - 1:
                    await self._async_sleep(self.RETRY_DELAY * (attempt + 1))
                    continue
        
        # All retries exhausted
        duration_ms = (time.time() - start_time) * 1000
        
        # Track failure
        if track_email_send:
            track_email_send(template_name, False, duration_ms / 1000)
        
        if raise_on_error:
            raise EmailSendError(last_error or "Email send failed after retries")
        
        return EmailResult(
            success=False, 
            error=last_error or "Email send failed after retries",
            error_code="RETRIES_EXHAUSTED",
            duration_ms=duration_ms
        )
    
    async def _async_sleep(self, seconds: float):
        """Async sleep helper."""
        import asyncio
        await asyncio.sleep(seconds)
    
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
            
        Raises:
            EmailTemplateError: If template rendering fails
        """
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)
        except TemplateNotFound:
            error_msg = f"Email template not found: {template_name}"
            logger.error(error_msg)
            raise EmailTemplateError(error_msg)
        except Exception as e:
            error_msg = f"Template render error for {template_name}: {e}"
            logger.error(error_msg)
            raise EmailTemplateError(error_msg)
    
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
        dashboard_url="https://nexusai.dev/dashboard",
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
