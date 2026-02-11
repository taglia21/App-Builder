"""
Valeric Analytics Module

Privacy-friendly analytics using Plausible.io and internal metrics tracking.
"""

from src.analytics.plausible import (
    Events,
    PlausibleClient,
    PlausibleEvent,
    get_plausible_client,
    get_plausible_script_tag,
    track,
)
from src.analytics.metrics import Metrics, get_metrics
from src.analytics.routes import router as analytics_router

__all__ = [
    "PlausibleClient",
    "PlausibleEvent",
    "Events",
    "get_plausible_client",
    "get_plausible_script_tag",
    "track",
    "Metrics",
    "get_metrics",
    "analytics_router",
]
