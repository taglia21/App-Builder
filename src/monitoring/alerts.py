"""
Alert Management

Provides alerting infrastructure for notifying on errors and issues.
"""

import os
import logging
from enum import Enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    """Alert delivery channels."""
    SLACK = "slack"
    EMAIL = "email"
    PAGERDUTY = "pagerduty"
    WEBHOOK = "webhook"
    SMS = "sms"


@dataclass
class Alert:
    """An alert to be sent."""
    title: str
    message: str
    severity: AlertSeverity
    
    # Source
    source: str = "launchforge"
    component: Optional[str] = None
    
    # Context
    error_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Metadata
    tags: Dict[str, str] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "message": self.message,
            "severity": self.severity.value,
            "source": self.source,
            "component": self.component,
            "error_id": self.error_id,
            "user_id": self.user_id,
            "tags": self.tags,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class Alerter(ABC):
    """Abstract base class for alerters."""
    
    @property
    @abstractmethod
    def channel(self) -> AlertChannel:
        """Alert channel type."""
        pass
    
    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """
        Send an alert.
        
        Args:
            alert: Alert to send.
        
        Returns:
            True if successfully sent.
        """
        pass


class SlackAlerter(Alerter):
    """Sends alerts to Slack."""
    
    def __init__(
        self,
        webhook_url: Optional[str] = None,
        channel: Optional[str] = None,
        username: str = "LaunchForge Alerts",
        min_severity: AlertSeverity = AlertSeverity.WARNING,
    ):
        self.webhook_url = webhook_url or os.getenv("SLACK_ALERT_WEBHOOK_URL")
        self.slack_channel = channel or os.getenv("SLACK_ALERT_CHANNEL")
        self.username = username
        self.min_severity = min_severity
    
    @property
    def channel(self) -> AlertChannel:
        return AlertChannel.SLACK
    
    def _should_send(self, alert: Alert) -> bool:
        """Check if alert meets minimum severity."""
        severity_order = [
            AlertSeverity.INFO,
            AlertSeverity.WARNING,
            AlertSeverity.ERROR,
            AlertSeverity.CRITICAL,
        ]
        return severity_order.index(alert.severity) >= severity_order.index(self.min_severity)
    
    def _format_message(self, alert: Alert) -> Dict[str, Any]:
        """Format alert for Slack."""
        color_map = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9800",
            AlertSeverity.ERROR: "#f44336",
            AlertSeverity.CRITICAL: "#9c27b0",
        }
        
        emoji_map = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.ERROR: "🚨",
            AlertSeverity.CRITICAL: "🔥",
        }
        
        fields = []
        
        if alert.component:
            fields.append({
                "title": "Component",
                "value": alert.component,
                "short": True,
            })
        
        if alert.error_id:
            fields.append({
                "title": "Error ID",
                "value": alert.error_id,
                "short": True,
            })
        
        for key, value in alert.tags.items():
            fields.append({
                "title": key.replace("_", " ").title(),
                "value": value,
                "short": True,
            })
        
        payload = {
            "username": self.username,
            "attachments": [{
                "color": color_map.get(alert.severity, "#808080"),
                "title": f"{emoji_map.get(alert.severity, '📢')} {alert.title}",
                "text": alert.message,
                "fields": fields,
                "footer": alert.source,
                "ts": int(alert.timestamp.timestamp()),
            }],
        }
        
        if self.slack_channel:
            payload["channel"] = self.slack_channel
        
        return payload
    
    async def send(self, alert: Alert) -> bool:
        """Send alert to Slack."""
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False
        
        if not self._should_send(alert):
            return True  # Skipped due to severity
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=self._format_message(alert),
                    timeout=10.0,
                )
                response.raise_for_status()
                return True
                
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False


class EmailAlerter(Alerter):
    """Sends alerts via email."""
    
    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None,
        to_emails: Optional[List[str]] = None,
        min_severity: AlertSeverity = AlertSeverity.ERROR,
    ):
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", str(smtp_port)))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.from_email = from_email or os.getenv("ALERT_FROM_EMAIL", "alerts@launchforge.dev")
        
        to_env = os.getenv("ALERT_TO_EMAILS", "")
        self.to_emails = to_emails or [e.strip() for e in to_env.split(",") if e.strip()]
        
        self.min_severity = min_severity
    
    @property
    def channel(self) -> AlertChannel:
        return AlertChannel.EMAIL
    
    def _should_send(self, alert: Alert) -> bool:
        """Check if alert meets minimum severity."""
        severity_order = [
            AlertSeverity.INFO,
            AlertSeverity.WARNING,
            AlertSeverity.ERROR,
            AlertSeverity.CRITICAL,
        ]
        return severity_order.index(alert.severity) >= severity_order.index(self.min_severity)
    
    def _format_email(self, alert: Alert) -> str:
        """Format alert as HTML email."""
        color_map = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9800",
            AlertSeverity.ERROR: "#f44336",
            AlertSeverity.CRITICAL: "#9c27b0",
        }
        
        details_html = ""
        if alert.details:
            details_html = "<h3>Details</h3><ul>"
            for k, v in alert.details.items():
                details_html += f"<li><strong>{k}:</strong> {v}</li>"
            details_html += "</ul>"
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="border-left: 4px solid {color_map.get(alert.severity, '#808080')}; padding-left: 15px;">
                <h2>{alert.title}</h2>
                <p><strong>Severity:</strong> {alert.severity.value.upper()}</p>
                <p><strong>Component:</strong> {alert.component or 'N/A'}</p>
                <p><strong>Time:</strong> {alert.timestamp.isoformat()}</p>
                <hr>
                <p>{alert.message}</p>
                {details_html}
            </div>
            <footer style="color: #666; margin-top: 20px;">
                <p>Sent by {alert.source}</p>
            </footer>
        </body>
        </html>
        """
    
    async def send(self, alert: Alert) -> bool:
        """Send alert via email."""
        if not all([self.smtp_host, self.to_emails]):
            logger.warning("Email alerter not fully configured")
            return False
        
        if not self._should_send(alert):
            return True
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.title}"
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.to_emails)
            
            html_content = self._format_email(alert)
            msg.attach(MIMEText(html_content, "html"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, self.to_emails, msg.as_string())
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False


class PagerDutyAlerter(Alerter):
    """Sends alerts to PagerDuty."""
    
    def __init__(
        self,
        routing_key: Optional[str] = None,
        min_severity: AlertSeverity = AlertSeverity.CRITICAL,
    ):
        self.routing_key = routing_key or os.getenv("PAGERDUTY_ROUTING_KEY")
        self.min_severity = min_severity
        self.api_url = "https://events.pagerduty.com/v2/enqueue"
    
    @property
    def channel(self) -> AlertChannel:
        return AlertChannel.PAGERDUTY
    
    def _should_send(self, alert: Alert) -> bool:
        """Check if alert meets minimum severity."""
        severity_order = [
            AlertSeverity.INFO,
            AlertSeverity.WARNING,
            AlertSeverity.ERROR,
            AlertSeverity.CRITICAL,
        ]
        return severity_order.index(alert.severity) >= severity_order.index(self.min_severity)
    
    def _format_event(self, alert: Alert) -> Dict[str, Any]:
        """Format alert for PagerDuty."""
        severity_map = {
            AlertSeverity.INFO: "info",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.ERROR: "error",
            AlertSeverity.CRITICAL: "critical",
        }
        
        return {
            "routing_key": self.routing_key,
            "event_action": "trigger",
            "dedup_key": alert.error_id or f"{alert.component}:{alert.title}",
            "payload": {
                "summary": alert.title,
                "source": alert.source,
                "severity": severity_map.get(alert.severity, "error"),
                "timestamp": alert.timestamp.isoformat(),
                "component": alert.component,
                "custom_details": {
                    "message": alert.message,
                    **alert.details,
                },
            },
        }
    
    async def send(self, alert: Alert) -> bool:
        """Send alert to PagerDuty."""
        if not self.routing_key:
            logger.warning("PagerDuty routing key not configured")
            return False
        
        if not self._should_send(alert):
            return True
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json=self._format_event(alert),
                    timeout=10.0,
                )
                response.raise_for_status()
                return True
                
        except Exception as e:
            logger.error(f"Failed to send PagerDuty alert: {e}")
            return False


class AlertManager:
    """
    Manages alert routing and delivery.
    
    Routes alerts to appropriate channels based on severity and configuration.
    """
    
    def __init__(self):
        self._alerters: List[Alerter] = []
        self._history: List[Alert] = []
        self._max_history: int = 100
    
    def add_alerter(self, alerter: Alerter) -> None:
        """Add an alerter."""
        self._alerters.append(alerter)
        logger.info(f"Added alerter: {alerter.channel.value}")
    
    async def send_alert(self, alert: Alert) -> Dict[str, bool]:
        """
        Send alert through all configured channels.
        
        Args:
            alert: Alert to send.
        
        Returns:
            Dictionary of channel -> success status.
        """
        results = {}
        
        for alerter in self._alerters:
            try:
                success = await alerter.send(alert)
                results[alerter.channel.value] = success
            except Exception as e:
                logger.error(f"Alerter {alerter.channel.value} failed: {e}")
                results[alerter.channel.value] = False
        
        # Track history
        self._history.append(alert)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        
        return results
    
    async def send_error_alert(
        self,
        title: str,
        message: str,
        error_id: Optional[str] = None,
        component: Optional[str] = None,
        **kwargs
    ) -> Dict[str, bool]:
        """Convenience method for error alerts."""
        alert = Alert(
            title=title,
            message=message,
            severity=AlertSeverity.ERROR,
            error_id=error_id,
            component=component,
            **kwargs
        )
        return await self.send_alert(alert)
    
    async def send_critical_alert(
        self,
        title: str,
        message: str,
        error_id: Optional[str] = None,
        component: Optional[str] = None,
        **kwargs
    ) -> Dict[str, bool]:
        """Convenience method for critical alerts."""
        alert = Alert(
            title=title,
            message=message,
            severity=AlertSeverity.CRITICAL,
            error_id=error_id,
            component=component,
            **kwargs
        )
        return await self.send_alert(alert)
    
    def get_history(
        self,
        severity: Optional[AlertSeverity] = None,
        limit: int = 50,
    ) -> List[Alert]:
        """
        Get alert history.
        
        Args:
            severity: Filter by severity.
            limit: Maximum alerts to return.
        
        Returns:
            List of recent alerts.
        """
        history = self._history
        
        if severity:
            history = [a for a in history if a.severity == severity]
        
        return history[-limit:]


def create_alert_manager(
    slack_webhook: Optional[str] = None,
    pagerduty_key: Optional[str] = None,
    email_config: Optional[Dict[str, Any]] = None,
) -> AlertManager:
    """
    Create an alert manager with common configurations.
    
    Args:
        slack_webhook: Slack webhook URL.
        pagerduty_key: PagerDuty routing key.
        email_config: Email configuration dictionary.
    
    Returns:
        Configured AlertManager.
    """
    manager = AlertManager()
    
    # Always add Slack if configured
    slack_url = slack_webhook or os.getenv("SLACK_ALERT_WEBHOOK_URL")
    if slack_url:
        manager.add_alerter(SlackAlerter(webhook_url=slack_url))
    
    # Add PagerDuty for critical alerts
    pd_key = pagerduty_key or os.getenv("PAGERDUTY_ROUTING_KEY")
    if pd_key:
        manager.add_alerter(PagerDutyAlerter(routing_key=pd_key))
    
    # Add email if configured
    if email_config or os.getenv("SMTP_HOST"):
        manager.add_alerter(EmailAlerter(**(email_config or {})))
    
    return manager
