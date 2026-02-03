"""Analytics API routes."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.analytics.metrics import get_metrics


router = APIRouter(tags=["analytics"])


class DashboardResponse(BaseModel):
    """Dashboard analytics response."""
    overview: dict
    metrics: dict
    summary: dict


class MetricsResponse(BaseModel):
    """Metrics response."""
    total_events: int
    event_types: dict
    last_event_time: Optional[str] = None


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)")
):
    """
    Get analytics dashboard data.
    
    Returns overview of all analytics metrics including:
    - Total events
    - Event breakdown by type
    - User engagement metrics
    """
    metrics = get_metrics()
    summary = metrics.get_summary()
    
    # Parse date filters if provided
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            pass
    
    # Get filtered events
    events = metrics.get_events(start_date=start_dt, end_date=end_dt)
    
    return {
        "overview": {
            "total_events": len(events),
            "date_range": {
                "start": start_date,
                "end": end_date
            }
        },
        "metrics": summary,
        "summary": {
            "app_generations": len([e for e in events if e.get("event") == "app_generation"]),
            "user_signups": len([e for e in events if e.get("event") == "user_signup"]),
            "subscription_changes": len([e for e in events if e.get("event") == "subscription_change"])
        }
    }


@router.get("/metrics", response_model=MetricsResponse)
async def get_analytics_metrics():
    """
    Get analytics metrics summary.
    
    Returns aggregated metrics data.
    """
    metrics = get_metrics()
    summary = metrics.get_summary()
    
    return MetricsResponse(
        total_events=summary["total_events"],
        event_types=summary["event_types"],
        last_event_time=summary["last_event_time"]
    )


@router.get("/events")
async def get_events(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(100, le=1000, description="Maximum number of events to return")
):
    """
    Get analytics events with optional filtering.
    
    Returns a list of tracked events.
    """
    metrics = get_metrics()
    events = metrics.get_events(user_id=user_id, event_type=event_type)
    
    # Apply limit
    events = events[:limit]
    
    return {
        "events": events,
        "total": len(events),
        "limit": limit
    }


@router.get("/users/{user_id}")
async def get_user_analytics(user_id: int):
    """
    Get analytics for a specific user.
    
    Returns user-specific metrics and events.
    """
    metrics = get_metrics()
    user_events = metrics.get_events(user_id=user_id)
    
    if not user_events:
        return {
            "user_id": user_id,
            "total_events": 0,
            "events": []
        }
    
    event_types = {}
    for event in user_events:
        event_type = event.get("event", "unknown")
        event_types[event_type] = event_types.get(event_type, 0) + 1
    
    return {
        "user_id": user_id,
        "total_events": len(user_events),
        "event_types": event_types,
        "recent_events": user_events[:10]  # Last 10 events
    }
