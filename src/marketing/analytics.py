"""Analytics tracking and reporting.

Supports multiple analytics providers: Google Analytics, Plausible, Mixpanel.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(str, Enum):
    """Standard analytics event types."""
    
    PAGE_VIEW = "page_view"
    CLICK = "click"
    SIGNUP = "signup"
    LOGIN = "login"
    PURCHASE = "purchase"
    SUBSCRIPTION = "subscription"
    DOWNLOAD = "download"
    SHARE = "share"
    SEARCH = "search"
    ERROR = "error"
    CUSTOM = "custom"


@dataclass
class AnalyticsEvent:
    """Single analytics event."""
    
    event_type: EventType
    name: str
    properties: dict[str, Any] = field(default_factory=dict)
    user_id: str | None = None
    session_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event": self.name,
            "type": self.event_type.value,
            "properties": self.properties,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AnalyticsConfig:
    """Analytics configuration."""
    
    enabled: bool = True
    debug: bool = False
    batch_size: int = 10
    flush_interval_seconds: int = 30


class AnalyticsProvider(ABC):
    """Base class for analytics providers."""
    
    def __init__(self, config: AnalyticsConfig | None = None):
        self.config = config or AnalyticsConfig()
        self._queue: list[AnalyticsEvent] = []
    
    @abstractmethod
    async def track(self, event: AnalyticsEvent) -> bool:
        """Track an analytics event."""
        pass
    
    @abstractmethod
    async def identify(self, user_id: str, traits: dict[str, Any]) -> bool:
        """Identify a user with traits."""
        pass
    
    @abstractmethod
    async def page(
        self,
        path: str,
        title: str | None = None,
        referrer: str | None = None,
    ) -> bool:
        """Track a page view."""
        pass
    
    async def flush(self) -> int:
        """Flush queued events."""
        count = len(self._queue)
        self._queue.clear()
        return count


class GoogleAnalytics(AnalyticsProvider):
    """Google Analytics 4 integration."""
    
    def __init__(
        self,
        measurement_id: str,
        api_secret: str | None = None,
        config: AnalyticsConfig | None = None,
    ):
        super().__init__(config)
        self.measurement_id = measurement_id
        self.api_secret = api_secret
        self._base_url = "https://www.google-analytics.com/mp/collect"
    
    async def track(self, event: AnalyticsEvent) -> bool:
        """Track event in GA4."""
        if not self.config.enabled:
            return False
        
        if not self.api_secret:
            # Client-side only, queue for batch
            self._queue.append(event)
            return True
        
        # Server-side tracking
        try:
            import httpx
            
            payload = {
                "client_id": event.session_id or "anonymous",
                "events": [{
                    "name": event.name,
                    "params": event.properties,
                }],
            }
            
            if event.user_id:
                payload["user_id"] = event.user_id
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._base_url,
                    params={
                        "measurement_id": self.measurement_id,
                        "api_secret": self.api_secret,
                    },
                    json=payload,
                )
                return response.status_code == 204
        except Exception:
            return False
    
    async def identify(self, user_id: str, traits: dict[str, Any]) -> bool:
        """Identify user in GA4."""
        # GA4 uses user_id in events
        return True
    
    async def page(
        self,
        path: str,
        title: str | None = None,
        referrer: str | None = None,
    ) -> bool:
        """Track page view in GA4."""
        event = AnalyticsEvent(
            event_type=EventType.PAGE_VIEW,
            name="page_view",
            properties={
                "page_location": path,
                "page_title": title or path,
                "page_referrer": referrer,
            },
        )
        return await self.track(event)
    
    def get_tracking_script(self) -> str:
        """Get client-side tracking script."""
        return f'''
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id={self.measurement_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{self.measurement_id}');
</script>
'''


class PlausibleAnalytics(AnalyticsProvider):
    """Plausible Analytics integration (privacy-friendly)."""
    
    def __init__(
        self,
        domain: str,
        api_key: str | None = None,
        custom_domain: str | None = None,
        config: AnalyticsConfig | None = None,
    ):
        super().__init__(config)
        self.domain = domain
        self.api_key = api_key
        self.script_domain = custom_domain or "plausible.io"
        self._base_url = f"https://{self.script_domain}/api/event"
    
    async def track(self, event: AnalyticsEvent) -> bool:
        """Track event in Plausible."""
        if not self.config.enabled:
            return False
        
        try:
            import httpx
            
            payload = {
                "name": event.name,
                "domain": self.domain,
                "url": event.properties.get("url", "/"),
                "props": event.properties,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._base_url,
                    json=payload,
                    headers={"User-Agent": "NexusAI/1.0"},
                )
                return response.status_code == 202
        except Exception:
            return False
    
    async def identify(self, user_id: str, traits: dict[str, Any]) -> bool:
        """Plausible doesn't track users - privacy first."""
        return True
    
    async def page(
        self,
        path: str,
        title: str | None = None,
        referrer: str | None = None,
    ) -> bool:
        """Track page view in Plausible."""
        event = AnalyticsEvent(
            event_type=EventType.PAGE_VIEW,
            name="pageview",
            properties={"url": path, "referrer": referrer},
        )
        return await self.track(event)
    
    def get_tracking_script(self) -> str:
        """Get client-side tracking script."""
        return f'''
<!-- Plausible Analytics -->
<script defer data-domain="{self.domain}" src="https://{self.script_domain}/js/script.js"></script>
'''


class MixpanelAnalytics(AnalyticsProvider):
    """Mixpanel Analytics integration."""
    
    def __init__(
        self,
        token: str,
        api_secret: str | None = None,
        config: AnalyticsConfig | None = None,
    ):
        super().__init__(config)
        self.token = token
        self.api_secret = api_secret
        self._base_url = "https://api.mixpanel.com"
    
    async def track(self, event: AnalyticsEvent) -> bool:
        """Track event in Mixpanel."""
        if not self.config.enabled:
            return False
        
        try:
            import httpx
            import base64
            
            payload = {
                "event": event.name,
                "properties": {
                    "token": self.token,
                    "distinct_id": event.user_id or event.session_id or "anonymous",
                    "time": int(event.timestamp.timestamp()),
                    **event.properties,
                },
            }
            
            data = base64.b64encode(
                str([payload]).encode()
            ).decode()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._base_url}/track",
                    params={"data": data},
                )
                return response.status_code == 200
        except Exception:
            return False
    
    async def identify(self, user_id: str, traits: dict[str, Any]) -> bool:
        """Identify user in Mixpanel."""
        if not self.config.enabled:
            return False
        
        try:
            import httpx
            import base64
            
            payload = {
                "$token": self.token,
                "$distinct_id": user_id,
                "$set": traits,
            }
            
            data = base64.b64encode(
                str([payload]).encode()
            ).decode()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._base_url}/engage",
                    params={"data": data},
                )
                return response.status_code == 200
        except Exception:
            return False
    
    async def page(
        self,
        path: str,
        title: str | None = None,
        referrer: str | None = None,
    ) -> bool:
        """Track page view in Mixpanel."""
        event = AnalyticsEvent(
            event_type=EventType.PAGE_VIEW,
            name="Page View",
            properties={
                "path": path,
                "title": title or path,
                "referrer": referrer,
            },
        )
        return await self.track(event)
    
    def get_tracking_script(self) -> str:
        """Get client-side tracking script."""
        return f'''
<!-- Mixpanel Analytics -->
<script>
(function(f,b){{if(!b.__SV){{var e,g,i,h;window.mixpanel=b;b._i=[];b.init=function(e,f,c){{function g(a,d){{var b=d.split(".");2==b.length&&(a=a[b[0]],d=b[1]);a[d]=function(){{a.push([d].concat(Array.prototype.slice.call(arguments,0)))}}}}var a=b;"undefined"!==typeof c?a=b[c]=[]:c="mixpanel";a.people=a.people||[];a.toString=function(a){{var d="mixpanel";"mixpanel"!==c&&(d+="."+c);a||(d+=" (stub)");return d}};a.people.toString=function(){{return a.toString(1)+".people (stub)"}};i="disable time_event track track_pageview track_links track_forms track_with_groups add_group set_group remove_group register register_once alias unregister identify name_tag set_config reset opt_in_tracking opt_out_tracking has_opted_in_tracking has_opted_out_tracking clear_opt_in_out_tracking start_batch_senders people.set people.set_once people.unset people.increment people.append people.union people.track_charge people.clear_charges people.delete_user people.remove".split(" ");for(h=0;h<i.length;h++)g(a,i[h]);var j="set set_once union unset remove delete".split(" ");a.get_group=function(){{function b(c){{d[c]=function(){{call2_args=arguments;call2=[c].concat(Array.prototype.slice.call(call2_args,0));a.push([e,call2])}}}}for(var d={{}},e=["get_group"].concat(Array.prototype.slice.call(arguments,0)),c=0;c<j.length;c++)b(j[c]);return d}};b._i.push([e,f,c])}};b.__SV=1.2;e=f.createElement("script");e.type="text/javascript";e.async=!0;e.src="https://cdn.mxpnl.com/libs/mixpanel-2-latest.min.js";g=f.getElementsByTagName("script")[0];g.parentNode.insertBefore(e,g)}}}})
(document,window.mixpanel||[]);
mixpanel.init("{self.token}");
</script>
'''


class MockAnalytics(AnalyticsProvider):
    """Mock analytics for testing."""
    
    def __init__(self, config: AnalyticsConfig | None = None):
        super().__init__(config)
        self.events: list[AnalyticsEvent] = []
        self.identified_users: dict[str, dict[str, Any]] = {}
        self.page_views: list[dict[str, Any]] = []
    
    async def track(self, event: AnalyticsEvent) -> bool:
        """Track event (mock)."""
        self.events.append(event)
        return True
    
    async def identify(self, user_id: str, traits: dict[str, Any]) -> bool:
        """Identify user (mock)."""
        self.identified_users[user_id] = traits
        return True
    
    async def page(
        self,
        path: str,
        title: str | None = None,
        referrer: str | None = None,
    ) -> bool:
        """Track page view (mock)."""
        self.page_views.append({
            "path": path,
            "title": title,
            "referrer": referrer,
        })
        return True


class AnalyticsTracker:
    """Unified analytics tracker supporting multiple providers."""
    
    def __init__(self, providers: list[AnalyticsProvider] | None = None):
        self.providers = providers or []
    
    def add_provider(self, provider: AnalyticsProvider) -> None:
        """Add an analytics provider."""
        self.providers.append(provider)
    
    async def track(
        self,
        event_name: str,
        properties: dict[str, Any] | None = None,
        user_id: str | None = None,
        event_type: EventType = EventType.CUSTOM,
    ) -> list[bool]:
        """Track event across all providers."""
        event = AnalyticsEvent(
            event_type=event_type,
            name=event_name,
            properties=properties or {},
            user_id=user_id,
        )
        
        results = []
        for provider in self.providers:
            result = await provider.track(event)
            results.append(result)
        
        return results
    
    async def identify(self, user_id: str, traits: dict[str, Any]) -> list[bool]:
        """Identify user across all providers."""
        results = []
        for provider in self.providers:
            result = await provider.identify(user_id, traits)
            results.append(result)
        return results
    
    async def page(
        self,
        path: str,
        title: str | None = None,
        referrer: str | None = None,
    ) -> list[bool]:
        """Track page view across all providers."""
        results = []
        for provider in self.providers:
            result = await provider.page(path, title, referrer)
            results.append(result)
        return results
    
    # Convenience methods for common events
    async def track_signup(
        self,
        user_id: str,
        method: str = "email",
        **properties: Any,
    ) -> list[bool]:
        """Track signup event."""
        return await self.track(
            "signup",
            {"method": method, **properties},
            user_id=user_id,
            event_type=EventType.SIGNUP,
        )
    
    async def track_login(
        self,
        user_id: str,
        method: str = "email",
        **properties: Any,
    ) -> list[bool]:
        """Track login event."""
        return await self.track(
            "login",
            {"method": method, **properties},
            user_id=user_id,
            event_type=EventType.LOGIN,
        )
    
    async def track_purchase(
        self,
        user_id: str,
        amount: float,
        currency: str = "USD",
        product: str = "",
        **properties: Any,
    ) -> list[bool]:
        """Track purchase event."""
        return await self.track(
            "purchase",
            {
                "amount": amount,
                "currency": currency,
                "product": product,
                **properties,
            },
            user_id=user_id,
            event_type=EventType.PURCHASE,
        )


def create_tracker(
    provider: str = "mock",
    **kwargs: Any,
) -> AnalyticsTracker:
    """Factory function to create analytics tracker."""
    providers_map = {
        "google": GoogleAnalytics,
        "ga": GoogleAnalytics,
        "plausible": PlausibleAnalytics,
        "mixpanel": MixpanelAnalytics,
        "mock": MockAnalytics,
    }
    
    provider_class = providers_map.get(provider.lower(), MockAnalytics)
    provider_instance = provider_class(**kwargs)
    
    return AnalyticsTracker(providers=[provider_instance])
