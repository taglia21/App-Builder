"""Analytics metrics collection and tracking."""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4


class Metrics:
    """In-memory metrics collection system."""

    def __init__(self):
        """Initialize metrics storage."""
        self._events: List[Dict[str, Any]] = []

    def track_app_generation(
        self,
        user_id: int,
        app_name: str,
        tech_stack: str,
        success: bool,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Track an app generation event."""
        event = {
            "id": str(uuid4()),
            "event": "app_generation",
            "user_id": user_id,
            "app_name": app_name,
            "tech_stack": tech_stack,
            "success": success,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self._events.append(event)
        return event

    def track_user_signup(
        self,
        user_id: int,
        email: str,
        signup_method: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Track a user signup event."""
        event = {
            "id": str(uuid4()),
            "event": "user_signup",
            "user_id": user_id,
            "email": email,
            "signup_method": signup_method,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self._events.append(event)
        return event

    def track_subscription_change(
        self,
        user_id: int,
        from_tier: str,
        to_tier: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Track a subscription tier change event."""
        event = {
            "id": str(uuid4()),
            "event": "subscription_change",
            "user_id": user_id,
            "from_tier": from_tier,
            "to_tier": to_tier,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self._events.append(event)
        return event

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all tracked metrics."""
        event_types = {}
        for event in self._events:
            event_type = event.get("event", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1

        return {
            "total_events": len(self._events),
            "event_types": event_types,
            "last_event_time": self._events[-1]["timestamp"] if self._events else None
        }

    def get_events(
        self,
        user_id: Optional[int] = None,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get events with optional filtering."""
        filtered_events = self._events

        if user_id is not None:
            filtered_events = [e for e in filtered_events if e.get("user_id") == user_id]

        if event_type is not None:
            filtered_events = [e for e in filtered_events if e.get("event") == event_type]

        if start_date is not None:
            start_str = start_date.isoformat()
            filtered_events = [e for e in filtered_events if e.get("timestamp", "") >= start_str]

        if end_date is not None:
            end_str = end_date.isoformat()
            filtered_events = [e for e in filtered_events if e.get("timestamp", "") <= end_str]

        return filtered_events


# Global metrics instance
_metrics_instance = None


def get_metrics() -> Metrics:
    """Get or create the global metrics instance."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = Metrics()
    return _metrics_instance
