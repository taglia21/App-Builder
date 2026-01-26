"""
Success Metrics Tracking

Track and analyze user success metrics for NexusAI.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics to track."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class EventType(str, Enum):
    """User event types."""
    # Acquisition
    SIGNUP = "signup"
    LOGIN = "login"
    
    # Activation
    PROJECT_CREATED = "project_created"
    FIRST_GENERATION = "first_generation"
    FIRST_DEPLOY = "first_deploy"
    
    # Engagement
    GENERATION_COMPLETED = "generation_completed"
    DEPLOYMENT_COMPLETED = "deployment_completed"
    CODE_EXPORTED = "code_exported"
    
    # Revenue
    SUBSCRIPTION_STARTED = "subscription_started"
    SUBSCRIPTION_UPGRADED = "subscription_upgraded"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    PAYMENT_RECEIVED = "payment_received"
    
    # Business Formation
    LLC_INITIATED = "llc_initiated"
    LLC_COMPLETED = "llc_completed"
    DOMAIN_REGISTERED = "domain_registered"
    BANK_ACCOUNT_OPENED = "bank_account_opened"
    
    # Retention
    RETURN_VISIT = "return_visit"
    FEATURE_USED = "feature_used"


@dataclass
class Metric:
    """A single metric data point."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }


@dataclass 
class Event:
    """A user event."""
    event_type: EventType
    user_id: Optional[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event": self.event_type.value,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "properties": self.properties,
        }


class MetricsCollector:
    """Collect and store metrics."""
    
    def __init__(self):
        self._metrics: List[Metric] = []
        self._events: List[Event] = []
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
    
    def increment(self, name: str, value: float = 1, tags: Dict[str, str] = None):
        """Increment a counter metric."""
        key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"
        self._counters[key] = self._counters.get(key, 0) + value
        
        self._metrics.append(Metric(
            name=name,
            value=self._counters[key],
            metric_type=MetricType.COUNTER,
            tags=tags or {},
        ))
    
    def gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric."""
        key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"
        self._gauges[key] = value
        
        self._metrics.append(Metric(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            tags=tags or {},
        ))
    
    def timing(self, name: str, duration_ms: float, tags: Dict[str, str] = None):
        """Record a timing metric."""
        self._metrics.append(Metric(
            name=name,
            value=duration_ms,
            metric_type=MetricType.TIMER,
            tags=tags or {},
        ))
    
    def track_event(self, event_type: EventType, user_id: str = None, **properties):
        """Track a user event."""
        event = Event(
            event_type=event_type,
            user_id=user_id,
            properties=properties,
        )
        self._events.append(event)
        logger.info(f"Event tracked: {event.to_dict()}")
        return event
    
    def get_metrics(self, since: datetime = None) -> List[Dict]:
        """Get all metrics since a timestamp."""
        metrics = self._metrics
        if since:
            metrics = [m for m in metrics if m.timestamp >= since]
        return [m.to_dict() for m in metrics]
    
    def get_events(self, since: datetime = None) -> List[Dict]:
        """Get all events since a timestamp."""
        events = self._events
        if since:
            events = [e for e in events if e.timestamp >= since]
        return [e.to_dict() for e in events]


class SuccessMetrics:
    """
    Track key success metrics for NexusAI.
    
    Key metrics:
    - Activation Rate: % of signups who create first project
    - Generation Success Rate: % of generations that complete
    - Deployment Rate: % of projects that get deployed
    - Time to First Deploy: Average time from signup to first deploy
    - Revenue per User: MRR / active users
    - Churn Rate: % of users who cancel
    """
    
    def __init__(self, collector: MetricsCollector = None):
        self.collector = collector or MetricsCollector()
    
    # ==================== Acquisition Metrics ====================
    
    def track_signup(self, user_id: str, source: str = None, **kwargs):
        """Track new user signup."""
        self.collector.increment("users.signups", tags={"source": source or "direct"})
        self.collector.track_event(
            EventType.SIGNUP,
            user_id=user_id,
            source=source,
            **kwargs
        )
    
    def track_login(self, user_id: str, method: str = "password"):
        """Track user login."""
        self.collector.increment("users.logins", tags={"method": method})
        self.collector.track_event(EventType.LOGIN, user_id=user_id, method=method)
    
    # ==================== Activation Metrics ====================
    
    def track_project_created(self, user_id: str, project_id: str, **kwargs):
        """Track project creation."""
        self.collector.increment("projects.created")
        self.collector.track_event(
            EventType.PROJECT_CREATED,
            user_id=user_id,
            project_id=project_id,
            **kwargs
        )
    
    def track_first_generation(self, user_id: str, project_id: str, duration_ms: float):
        """Track first AI generation for a user."""
        self.collector.increment("generations.first")
        self.collector.timing("generations.first.duration", duration_ms)
        self.collector.track_event(
            EventType.FIRST_GENERATION,
            user_id=user_id,
            project_id=project_id,
            duration_ms=duration_ms
        )
    
    def track_first_deploy(self, user_id: str, project_id: str, provider: str, duration_ms: float):
        """Track first deployment for a user."""
        self.collector.increment("deployments.first", tags={"provider": provider})
        self.collector.timing("deployments.first.duration", duration_ms)
        self.collector.track_event(
            EventType.FIRST_DEPLOY,
            user_id=user_id,
            project_id=project_id,
            provider=provider,
            duration_ms=duration_ms
        )
    
    # ==================== Engagement Metrics ====================
    
    def track_generation(self, user_id: str, project_id: str, success: bool, duration_ms: float):
        """Track AI generation."""
        status = "success" if success else "failed"
        self.collector.increment("generations.total", tags={"status": status})
        self.collector.timing("generations.duration", duration_ms, tags={"status": status})
        
        if success:
            self.collector.track_event(
                EventType.GENERATION_COMPLETED,
                user_id=user_id,
                project_id=project_id,
                duration_ms=duration_ms
            )
    
    def track_deployment(self, user_id: str, project_id: str, provider: str, success: bool):
        """Track deployment."""
        status = "success" if success else "failed"
        self.collector.increment("deployments.total", tags={"provider": provider, "status": status})
        
        if success:
            self.collector.track_event(
                EventType.DEPLOYMENT_COMPLETED,
                user_id=user_id,
                project_id=project_id,
                provider=provider
            )
    
    def track_code_export(self, user_id: str, project_id: str, format: str = "zip"):
        """Track code export."""
        self.collector.increment("exports.total", tags={"format": format})
        self.collector.track_event(
            EventType.CODE_EXPORTED,
            user_id=user_id,
            project_id=project_id,
            format=format
        )
    
    # ==================== Revenue Metrics ====================
    
    def track_subscription_started(self, user_id: str, plan: str, mrr: float):
        """Track new subscription."""
        self.collector.increment("subscriptions.started", tags={"plan": plan})
        self.collector.gauge("revenue.mrr_delta", mrr, tags={"type": "new"})
        self.collector.track_event(
            EventType.SUBSCRIPTION_STARTED,
            user_id=user_id,
            plan=plan,
            mrr=mrr
        )
    
    def track_subscription_upgraded(self, user_id: str, from_plan: str, to_plan: str, mrr_delta: float):
        """Track subscription upgrade."""
        self.collector.increment("subscriptions.upgraded")
        self.collector.gauge("revenue.mrr_delta", mrr_delta, tags={"type": "upgrade"})
        self.collector.track_event(
            EventType.SUBSCRIPTION_UPGRADED,
            user_id=user_id,
            from_plan=from_plan,
            to_plan=to_plan,
            mrr_delta=mrr_delta
        )
    
    def track_subscription_cancelled(self, user_id: str, plan: str, mrr_lost: float, reason: str = None):
        """Track subscription cancellation."""
        self.collector.increment("subscriptions.cancelled", tags={"plan": plan})
        self.collector.gauge("revenue.mrr_delta", -mrr_lost, tags={"type": "churn"})
        self.collector.track_event(
            EventType.SUBSCRIPTION_CANCELLED,
            user_id=user_id,
            plan=plan,
            mrr_lost=mrr_lost,
            reason=reason
        )
    
    def track_payment(self, user_id: str, amount: float, currency: str = "usd"):
        """Track payment received."""
        self.collector.increment("payments.total")
        self.collector.increment("payments.amount", value=amount, tags={"currency": currency})
        self.collector.track_event(
            EventType.PAYMENT_RECEIVED,
            user_id=user_id,
            amount=amount,
            currency=currency
        )
    
    # ==================== Business Formation Metrics ====================
    
    def track_llc_initiated(self, user_id: str, state: str):
        """Track LLC formation started."""
        self.collector.increment("business.llc_initiated", tags={"state": state})
        self.collector.track_event(EventType.LLC_INITIATED, user_id=user_id, state=state)
    
    def track_llc_completed(self, user_id: str, state: str, duration_days: int):
        """Track LLC formation completed."""
        self.collector.increment("business.llc_completed", tags={"state": state})
        self.collector.gauge("business.llc_duration_days", duration_days)
        self.collector.track_event(
            EventType.LLC_COMPLETED,
            user_id=user_id,
            state=state,
            duration_days=duration_days
        )
    
    def track_domain_registered(self, user_id: str, domain: str, registrar: str):
        """Track domain registration."""
        self.collector.increment("business.domains_registered")
        self.collector.track_event(
            EventType.DOMAIN_REGISTERED,
            user_id=user_id,
            domain=domain,
            registrar=registrar
        )
    
    def track_bank_account_opened(self, user_id: str, bank: str):
        """Track business bank account opened."""
        self.collector.increment("business.bank_accounts_opened", tags={"bank": bank})
        self.collector.track_event(
            EventType.BANK_ACCOUNT_OPENED,
            user_id=user_id,
            bank=bank
        )
    
    # ==================== Computed Metrics ====================
    
    def get_activation_rate(self, since: datetime = None) -> float:
        """Calculate activation rate (signups who create project)."""
        events = self.collector.get_events(since)
        signups = len([e for e in events if e.get("event") == EventType.SIGNUP.value])
        activations = len([e for e in events if e.get("event") == EventType.PROJECT_CREATED.value])
        
        if signups == 0:
            return 0.0
        return (activations / signups) * 100
    
    def get_deployment_rate(self, since: datetime = None) -> float:
        """Calculate deployment rate (projects that get deployed)."""
        events = self.collector.get_events(since)
        projects = len([e for e in events if e.get("event") == EventType.PROJECT_CREATED.value])
        deployments = len([e for e in events if e.get("event") == EventType.DEPLOYMENT_COMPLETED.value])
        
        if projects == 0:
            return 0.0
        return (deployments / projects) * 100
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all key metrics."""
        last_30_days = datetime.utcnow() - timedelta(days=30)
        events = self.collector.get_events(last_30_days)
        
        return {
            "period": "last_30_days",
            "signups": len([e for e in events if e.get("event") == EventType.SIGNUP.value]),
            "projects_created": len([e for e in events if e.get("event") == EventType.PROJECT_CREATED.value]),
            "generations": len([e for e in events if e.get("event") == EventType.GENERATION_COMPLETED.value]),
            "deployments": len([e for e in events if e.get("event") == EventType.DEPLOYMENT_COMPLETED.value]),
            "subscriptions_started": len([e for e in events if e.get("event") == EventType.SUBSCRIPTION_STARTED.value]),
            "llcs_formed": len([e for e in events if e.get("event") == EventType.LLC_COMPLETED.value]),
            "activation_rate": self.get_activation_rate(last_30_days),
            "deployment_rate": self.get_deployment_rate(last_30_days),
        }


# Global instance
metrics = SuccessMetrics()


# Convenience functions
def track_signup(user_id: str, **kwargs):
    return metrics.track_signup(user_id, **kwargs)

def track_project_created(user_id: str, project_id: str, **kwargs):
    return metrics.track_project_created(user_id, project_id, **kwargs)

def track_generation(user_id: str, project_id: str, success: bool, duration_ms: float):
    return metrics.track_generation(user_id, project_id, success, duration_ms)

def track_deployment(user_id: str, project_id: str, provider: str, success: bool):
    return metrics.track_deployment(user_id, project_id, provider, success)

def track_subscription(user_id: str, plan: str, mrr: float):
    return metrics.track_subscription_started(user_id, plan, mrr)

def get_metrics_summary() -> Dict[str, Any]:
    return metrics.get_summary()
