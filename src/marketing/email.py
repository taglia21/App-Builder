"""Email marketing and transactional email.

Supports Resend, SendGrid, and mock provider for testing.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EmailStatus(str, Enum):
    """Email delivery status."""
    
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    FAILED = "failed"


class TemplateType(str, Enum):
    """Email template types."""
    
    WELCOME = "welcome"
    VERIFICATION = "verification"
    PASSWORD_RESET = "password_reset"
    INVOICE = "invoice"
    SUBSCRIPTION = "subscription"
    NOTIFICATION = "notification"
    MARKETING = "marketing"
    NEWSLETTER = "newsletter"
    CUSTOM = "custom"


@dataclass
class EmailTemplate:
    """Email template with variables."""
    
    name: str
    template_type: TemplateType
    subject: str
    html_body: str
    text_body: str | None = None
    variables: list[str] = field(default_factory=list)
    
    def render(self, data: dict[str, Any]) -> tuple[str, str, str | None]:
        """Render template with data.
        
        Returns (subject, html_body, text_body)
        """
        subject = self.subject
        html = self.html_body
        text = self.text_body
        
        for key, value in data.items():
            placeholder = f"{{{{{key}}}}}"
            subject = subject.replace(placeholder, str(value))
            html = html.replace(placeholder, str(value))
            if text:
                text = text.replace(placeholder, str(value))
        
        return subject, html, text


@dataclass
class EmailRecipient:
    """Email recipient."""
    
    email: str
    name: str | None = None
    
    def __str__(self) -> str:
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email


@dataclass
class EmailMessage:
    """Email message."""
    
    to: list[EmailRecipient]
    subject: str
    html_body: str
    text_body: str | None = None
    from_email: str = "noreply@nexusai.dev"
    from_name: str = "LaunchForge"
    reply_to: str | None = None
    cc: list[EmailRecipient] = field(default_factory=list)
    bcc: list[EmailRecipient] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EmailResult:
    """Result of sending an email."""
    
    message_id: str
    status: EmailStatus
    recipient: str
    sent_at: datetime = field(default_factory=datetime.utcnow)
    error: str | None = None


@dataclass
class EmailCampaign:
    """Email marketing campaign."""
    
    id: str
    name: str
    subject: str
    template: EmailTemplate
    recipients: list[EmailRecipient]
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    status: str = "draft"
    stats: dict[str, int] = field(default_factory=lambda: {
        "sent": 0,
        "delivered": 0,
        "opened": 0,
        "clicked": 0,
        "bounced": 0,
    })


class EmailProvider(ABC):
    """Base class for email providers."""
    
    @abstractmethod
    async def send(self, message: EmailMessage) -> list[EmailResult]:
        """Send an email message."""
        pass
    
    @abstractmethod
    async def send_batch(
        self,
        messages: list[EmailMessage],
    ) -> list[EmailResult]:
        """Send multiple email messages."""
        pass
    
    async def send_template(
        self,
        template: EmailTemplate,
        to: list[EmailRecipient],
        data: dict[str, Any],
        from_email: str = "noreply@nexusai.dev",
        from_name: str = "LaunchForge",
    ) -> list[EmailResult]:
        """Send email using a template."""
        subject, html, text = template.render(data)
        
        message = EmailMessage(
            to=to,
            subject=subject,
            html_body=html,
            text_body=text,
            from_email=from_email,
            from_name=from_name,
        )
        
        return await self.send(message)


class ResendProvider(EmailProvider):
    """Resend email provider."""
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self._base_url = "https://api.resend.com"
    
    async def send(self, message: EmailMessage) -> list[EmailResult]:
        """Send email via Resend."""
        if not self.api_key:
            return [EmailResult(
                message_id="",
                status=EmailStatus.FAILED,
                recipient=r.email,
                error="No API key configured",
            ) for r in message.to]
        
        try:
            import httpx
            
            payload = {
                "from": f"{message.from_name} <{message.from_email}>",
                "to": [str(r) for r in message.to],
                "subject": message.subject,
                "html": message.html_body,
            }
            
            if message.text_body:
                payload["text"] = message.text_body
            
            if message.reply_to:
                payload["reply_to"] = message.reply_to
            
            if message.cc:
                payload["cc"] = [str(r) for r in message.cc]
            
            if message.bcc:
                payload["bcc"] = [str(r) for r in message.bcc]
            
            if message.tags:
                payload["tags"] = [{"name": t} for t in message.tags]
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/emails",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return [EmailResult(
                        message_id=data.get("id", ""),
                        status=EmailStatus.SENT,
                        recipient=r.email,
                    ) for r in message.to]
                else:
                    error = response.text
                    return [EmailResult(
                        message_id="",
                        status=EmailStatus.FAILED,
                        recipient=r.email,
                        error=error,
                    ) for r in message.to]
        except Exception as e:
            return [EmailResult(
                message_id="",
                status=EmailStatus.FAILED,
                recipient=r.email,
                error=str(e),
            ) for r in message.to]
    
    async def send_batch(
        self,
        messages: list[EmailMessage],
    ) -> list[EmailResult]:
        """Send multiple emails via Resend."""
        results = []
        for message in messages:
            result = await self.send(message)
            results.extend(result)
        return results


class SendGridProvider(EmailProvider):
    """SendGrid email provider."""
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self._base_url = "https://api.sendgrid.com/v3"
    
    async def send(self, message: EmailMessage) -> list[EmailResult]:
        """Send email via SendGrid."""
        if not self.api_key:
            return [EmailResult(
                message_id="",
                status=EmailStatus.FAILED,
                recipient=r.email,
                error="No API key configured",
            ) for r in message.to]
        
        try:
            import httpx
            
            payload = {
                "personalizations": [{
                    "to": [{"email": r.email, "name": r.name} for r in message.to],
                }],
                "from": {
                    "email": message.from_email,
                    "name": message.from_name,
                },
                "subject": message.subject,
                "content": [
                    {"type": "text/html", "value": message.html_body},
                ],
            }
            
            if message.text_body:
                payload["content"].insert(0, {
                    "type": "text/plain",
                    "value": message.text_body,
                })
            
            if message.cc:
                payload["personalizations"][0]["cc"] = [
                    {"email": r.email, "name": r.name} for r in message.cc
                ]
            
            if message.bcc:
                payload["personalizations"][0]["bcc"] = [
                    {"email": r.email, "name": r.name} for r in message.bcc
                ]
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/mail/send",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                
                if response.status_code in (200, 202):
                    message_id = response.headers.get("X-Message-Id", "")
                    return [EmailResult(
                        message_id=message_id,
                        status=EmailStatus.SENT,
                        recipient=r.email,
                    ) for r in message.to]
                else:
                    error = response.text
                    return [EmailResult(
                        message_id="",
                        status=EmailStatus.FAILED,
                        recipient=r.email,
                        error=error,
                    ) for r in message.to]
        except Exception as e:
            return [EmailResult(
                message_id="",
                status=EmailStatus.FAILED,
                recipient=r.email,
                error=str(e),
            ) for r in message.to]
    
    async def send_batch(
        self,
        messages: list[EmailMessage],
    ) -> list[EmailResult]:
        """Send multiple emails via SendGrid."""
        results = []
        for message in messages:
            result = await self.send(message)
            results.extend(result)
        return results


class MockEmailProvider(EmailProvider):
    """Mock email provider for testing."""
    
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.sent_messages: list[EmailMessage] = []
        self.sent_count = 0
    
    async def send(self, message: EmailMessage) -> list[EmailResult]:
        """Send email (mock)."""
        if self.should_fail:
            return [EmailResult(
                message_id="",
                status=EmailStatus.FAILED,
                recipient=r.email,
                error="Mock failure",
            ) for r in message.to]
        
        self.sent_messages.append(message)
        self.sent_count += len(message.to)
        
        return [EmailResult(
            message_id=f"mock_{self.sent_count}_{i}",
            status=EmailStatus.SENT,
            recipient=r.email,
        ) for i, r in enumerate(message.to)]
    
    async def send_batch(
        self,
        messages: list[EmailMessage],
    ) -> list[EmailResult]:
        """Send multiple emails (mock)."""
        results = []
        for message in messages:
            result = await self.send(message)
            results.extend(result)
        return results


# Pre-built templates
TEMPLATES = {
    "welcome": EmailTemplate(
        name="Welcome Email",
        template_type=TemplateType.WELCOME,
        subject="Welcome to {{app_name}}!",
        html_body="""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #4F46E5; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background: #4F46E5; color: white; text-decoration: none; border-radius: 6px; }
        .footer { padding: 20px; text-align: center; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to {{app_name}}!</h1>
        </div>
        <div class="content">
            <p>Hi {{user_name}},</p>
            <p>Thanks for signing up! We're excited to have you on board.</p>
            <p>Get started by creating your first project:</p>
            <p style="text-align: center;">
                <a href="{{dashboard_url}}" class="button">Go to Dashboard</a>
            </p>
        </div>
        <div class="footer">
            <p>© {{year}} {{app_name}}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
""",
        text_body="""
Welcome to {{app_name}}!

Hi {{user_name}},

Thanks for signing up! We're excited to have you on board.

Get started by creating your first project: {{dashboard_url}}

© {{year}} {{app_name}}. All rights reserved.
""",
        variables=["app_name", "user_name", "dashboard_url", "year"],
    ),
    
    "password_reset": EmailTemplate(
        name="Password Reset",
        template_type=TemplateType.PASSWORD_RESET,
        subject="Reset your {{app_name}} password",
        html_body="""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .content { padding: 20px; background: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background: #4F46E5; color: white; text-decoration: none; border-radius: 6px; }
        .warning { color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="content">
            <h2>Reset Your Password</h2>
            <p>Hi {{user_name}},</p>
            <p>We received a request to reset your password. Click the button below to create a new password:</p>
            <p style="text-align: center;">
                <a href="{{reset_url}}" class="button">Reset Password</a>
            </p>
            <p class="warning">This link expires in 1 hour. If you didn't request this, you can safely ignore this email.</p>
        </div>
    </div>
</body>
</html>
""",
        text_body="""
Reset Your Password

Hi {{user_name}},

We received a request to reset your password. 

Reset your password: {{reset_url}}

This link expires in 1 hour. If you didn't request this, you can safely ignore this email.
""",
        variables=["app_name", "user_name", "reset_url"],
    ),
}


class EmailService:
    """High-level email service."""
    
    def __init__(self, provider: EmailProvider):
        self.provider = provider
        self.templates = TEMPLATES.copy()
    
    def register_template(self, key: str, template: EmailTemplate) -> None:
        """Register a custom template."""
        self.templates[key] = template
    
    async def send_welcome(
        self,
        to_email: str,
        user_name: str,
        app_name: str = "LaunchForge",
        dashboard_url: str = "https://app.nexusai.dev/dashboard",
    ) -> EmailResult:
        """Send welcome email."""
        template = self.templates["welcome"]
        results = await self.provider.send_template(
            template=template,
            to=[EmailRecipient(email=to_email, name=user_name)],
            data={
                "app_name": app_name,
                "user_name": user_name,
                "dashboard_url": dashboard_url,
                "year": datetime.now().year,
            },
        )
        return results[0] if results else EmailResult(
            message_id="",
            status=EmailStatus.FAILED,
            recipient=to_email,
            error="No result returned",
        )
    
    async def send_password_reset(
        self,
        to_email: str,
        user_name: str,
        reset_url: str,
        app_name: str = "LaunchForge",
    ) -> EmailResult:
        """Send password reset email."""
        template = self.templates["password_reset"]
        results = await self.provider.send_template(
            template=template,
            to=[EmailRecipient(email=to_email, name=user_name)],
            data={
                "app_name": app_name,
                "user_name": user_name,
                "reset_url": reset_url,
            },
        )
        return results[0] if results else EmailResult(
            message_id="",
            status=EmailStatus.FAILED,
            recipient=to_email,
            error="No result returned",
        )
    
    async def send_notification(
        self,
        to_email: str,
        subject: str,
        message: str,
        action_url: str | None = None,
        action_text: str = "View Details",
    ) -> EmailResult:
        """Send a notification email."""
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .content {{ padding: 20px; background: #f9f9f9; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #4F46E5; color: white; text-decoration: none; border-radius: 6px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="content">
            <p>{message}</p>
            {"<p style='text-align: center;'><a href='" + action_url + "' class='button'>" + action_text + "</a></p>" if action_url else ""}
        </div>
    </div>
</body>
</html>
"""
        
        email_message = EmailMessage(
            to=[EmailRecipient(email=to_email)],
            subject=subject,
            html_body=html_body,
            text_body=message,
        )
        
        results = await self.provider.send(email_message)
        return results[0] if results else EmailResult(
            message_id="",
            status=EmailStatus.FAILED,
            recipient=to_email,
            error="No result returned",
        )


def create_email_service(
    provider: str = "mock",
    api_key: str | None = None,
) -> EmailService:
    """Factory function to create email service."""
    providers_map = {
        "resend": ResendProvider,
        "sendgrid": SendGridProvider,
        "mock": MockEmailProvider,
    }
    
    provider_class = providers_map.get(provider.lower(), MockEmailProvider)
    
    if provider.lower() == "mock":
        provider_instance = provider_class()
    else:
        provider_instance = provider_class(api_key=api_key)
    
    return EmailService(provider=provider_instance)
