"""
Plausible Analytics Integration.

Privacy-friendly analytics that:
- Doesn't use cookies
- Is GDPR compliant by default
- Respects Do Not Track
- Provides simple event tracking
"""

from typing import Optional, Dict, Any
import httpx
import logging
from dataclasses import dataclass

from src.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class PlausibleEvent:
    """A Plausible analytics event."""
    name: str
    url: str
    referrer: Optional[str] = None
    props: Optional[Dict[str, Any]] = None


class PlausibleClient:
    """
    Client for Plausible Analytics API.
    
    Features:
    - Server-side event tracking
    - Custom event properties
    - Goal tracking
    """
    
    PLAUSIBLE_API_URL = "https://plausible.io/api/event"
    
    def __init__(
        self,
        domain: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize Plausible client.
        
        Args:
            domain: Plausible site domain (e.g., 'launchforge.dev')
            api_key: Optional API key for stats access
        """
        settings = get_settings()
        self.domain = domain or getattr(settings, 'plausible_domain', None)
        self.api_key = api_key or getattr(settings, 'plausible_api_key', None)
        
    @property
    def is_configured(self) -> bool:
        """Check if analytics is configured."""
        return bool(self.domain)
    
    async def track_event(
        self,
        event_name: str,
        url: str,
        user_agent: str = "",
        ip_address: str = "",
        referrer: Optional[str] = None,
        props: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Track a custom event.
        
        Args:
            event_name: Name of the event (e.g., 'Signup', 'Generate App')
            url: Page URL where event occurred
            user_agent: User's browser user agent
            ip_address: User's IP address
            referrer: Referrer URL
            props: Custom properties
            
        Returns:
            True if event tracked successfully
        """
        if not self.is_configured:
            logger.debug("Plausible not configured - skipping event")
            return False
        
        payload = {
            "domain": self.domain,
            "name": event_name,
            "url": url,
        }
        
        if referrer:
            payload["referrer"] = referrer
            
        if props:
            payload["props"] = props
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": user_agent or "LaunchForge/1.0",
        }
        
        if ip_address:
            headers["X-Forwarded-For"] = ip_address
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.PLAUSIBLE_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=5.0
                )
                
                if response.status_code == 202:
                    logger.debug(f"Plausible event tracked: {event_name}")
                    return True
                else:
                    logger.warning(f"Plausible tracking failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.warning(f"Plausible tracking error: {e}")
            return False
    
    async def track_pageview(
        self,
        url: str,
        user_agent: str = "",
        ip_address: str = "",
        referrer: Optional[str] = None
    ) -> bool:
        """
        Track a page view.
        
        Args:
            url: Page URL
            user_agent: Browser user agent
            ip_address: User IP
            referrer: Referrer URL
            
        Returns:
            True if tracked successfully
        """
        return await self.track_event(
            event_name="pageview",
            url=url,
            user_agent=user_agent,
            ip_address=ip_address,
            referrer=referrer
        )


# Pre-defined events for LaunchForge
class Events:
    """Standard LaunchForge analytics events."""
    
    # User events
    SIGNUP = "Signup"
    LOGIN = "Login"
    LOGOUT = "Logout"
    EMAIL_VERIFIED = "Email Verified"
    
    # App generation events
    APP_STARTED = "App Generation Started"
    APP_COMPLETED = "App Generation Completed"
    APP_FAILED = "App Generation Failed"
    
    # Deployment events
    DEPLOY_STARTED = "Deployment Started"
    DEPLOY_COMPLETED = "Deployment Completed"
    DEPLOY_FAILED = "Deployment Failed"
    
    # Payment events
    SUBSCRIPTION_STARTED = "Subscription Started"
    SUBSCRIPTION_CANCELLED = "Subscription Cancelled"
    PAYMENT_COMPLETED = "Payment Completed"
    
    # Business events
    LLC_STARTED = "LLC Formation Started"
    LLC_COMPLETED = "LLC Formation Completed"
    
    # Engagement events
    FEEDBACK_SUBMITTED = "Feedback Submitted"
    DOCS_VIEWED = "Docs Viewed"
    API_KEY_ADDED = "API Key Added"


# Singleton instance
_plausible_client: Optional[PlausibleClient] = None


def get_plausible_client() -> PlausibleClient:
    """Get or create Plausible client singleton."""
    global _plausible_client
    if _plausible_client is None:
        _plausible_client = PlausibleClient()
    return _plausible_client


# Convenience function
async def track(
    event: str,
    url: str,
    user_agent: str = "",
    ip_address: str = "",
    referrer: Optional[str] = None,
    props: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Convenience function to track an event.
    
    Args:
        event: Event name (use Events class constants)
        url: Page URL
        user_agent: Browser user agent
        ip_address: User IP address
        referrer: Referrer URL
        props: Custom properties
        
    Returns:
        True if tracked successfully
    """
    client = get_plausible_client()
    return await client.track_event(
        event_name=event,
        url=url,
        user_agent=user_agent,
        ip_address=ip_address,
        referrer=referrer,
        props=props
    )


def get_plausible_script_tag(domain: Optional[str] = None) -> str:
    """
    Generate the Plausible script tag for HTML pages.
    
    Args:
        domain: Site domain (or from settings)
        
    Returns:
        HTML script tag or empty string if not configured
    """
    settings = get_settings()
    site_domain = domain or getattr(settings, 'plausible_domain', None)
    
    if not site_domain:
        return ""
    
    return f'''<script defer data-domain="{site_domain}" src="https://plausible.io/js/script.js"></script>'''
