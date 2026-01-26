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
            domain: Plausible site domain (e.g., 'nexusai.dev')
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
            "User-Agent": user_agent or "NexusAI/1.0",
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


# Pre-defined events for NexusAI
class Events:
    """Standard NexusAI analytics events."""
    
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


# =============================================================================
# GOOGLE ANALYTICS (GA4) SUPPORT
# =============================================================================

class GoogleAnalyticsClient:
    """
    Client for Google Analytics 4 (GA4).
    
    Features:
    - Server-side event tracking via Measurement Protocol
    - Client-side gtag.js integration
    - Custom event properties
    - E-commerce tracking support
    """
    
    GA4_MEASUREMENT_URL = "https://www.google-analytics.com/mp/collect"
    
    def __init__(
        self,
        measurement_id: Optional[str] = None,
        api_secret: Optional[str] = None
    ):
        """
        Initialize Google Analytics client.
        
        Args:
            measurement_id: GA4 Measurement ID (G-XXXXXXXXXX)
            api_secret: API secret for Measurement Protocol
        """
        settings = get_settings()
        self.measurement_id = measurement_id or getattr(settings, 'google_analytics_id', None)
        self.api_secret = api_secret or getattr(settings, 'google_analytics_api_secret', None)
        
    @property
    def is_configured(self) -> bool:
        """Check if GA4 is configured."""
        return bool(self.measurement_id)
    
    async def track_event(
        self,
        client_id: str,
        event_name: str,
        params: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Track an event via Measurement Protocol (server-side).
        
        Args:
            client_id: Unique client identifier
            event_name: Name of the event
            params: Event parameters
            user_id: Optional user ID for cross-device tracking
            
        Returns:
            True if event tracked successfully
        """
        if not self.is_configured or not self.api_secret:
            logger.debug("GA4 not configured for server-side tracking - skipping event")
            return False
        
        url = f"{self.GA4_MEASUREMENT_URL}?measurement_id={self.measurement_id}&api_secret={self.api_secret}"
        
        payload = {
            "client_id": client_id,
            "events": [{
                "name": event_name,
                "params": params or {}
            }]
        }
        
        if user_id:
            payload["user_id"] = user_id
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    timeout=5.0
                )
                
                if response.status_code in (200, 204):
                    logger.debug(f"GA4 event tracked: {event_name}")
                    return True
                else:
                    logger.warning(f"GA4 tracking failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.warning(f"GA4 tracking error: {e}")
            return False
    
    async def track_pageview(
        self,
        client_id: str,
        page_location: str,
        page_title: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Track a page view.
        
        Args:
            client_id: Unique client identifier
            page_location: Full URL of the page
            page_title: Page title
            user_id: Optional user ID
            
        Returns:
            True if tracked successfully
        """
        params = {
            "page_location": page_location,
        }
        if page_title:
            params["page_title"] = page_title
            
        return await self.track_event(
            client_id=client_id,
            event_name="page_view",
            params=params,
            user_id=user_id
        )


# Singleton instance
_ga_client: Optional[GoogleAnalyticsClient] = None


def get_ga_client() -> GoogleAnalyticsClient:
    """Get or create Google Analytics client singleton."""
    global _ga_client
    if _ga_client is None:
        _ga_client = GoogleAnalyticsClient()
    return _ga_client


def get_google_analytics_script_tag(measurement_id: Optional[str] = None) -> str:
    """
    Generate the Google Analytics 4 gtag.js script tags for HTML pages.
    
    Args:
        measurement_id: GA4 Measurement ID (or from settings)
        
    Returns:
        HTML script tags or empty string if not configured
    """
    settings = get_settings()
    ga_id = measurement_id or getattr(settings, 'google_analytics_id', None)
    
    if not ga_id:
        return ""
    
    return f'''<!-- Google Analytics 4 -->
<script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  
  // Default to denied, update based on cookie consent
  gtag('consent', 'default', {{
    'analytics_storage': 'denied',
    'ad_storage': 'denied'
  }});
  
  gtag('config', '{ga_id}', {{
    'anonymize_ip': true,
    'cookie_flags': 'SameSite=None;Secure'
  }});
</script>'''


def get_all_analytics_script_tags(
    plausible_domain: Optional[str] = None,
    google_analytics_id: Optional[str] = None
) -> str:
    """
    Generate all configured analytics script tags.
    
    Args:
        plausible_domain: Plausible site domain
        google_analytics_id: GA4 Measurement ID
        
    Returns:
        Combined HTML script tags for all configured analytics
    """
    scripts = []
    
    plausible_tag = get_plausible_script_tag(plausible_domain)
    if plausible_tag:
        scripts.append(plausible_tag)
    
    ga_tag = get_google_analytics_script_tag(google_analytics_id)
    if ga_tag:
        scripts.append(ga_tag)
    
    return "\n".join(scripts)
