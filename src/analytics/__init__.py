"""
NexusAI Analytics Module

Privacy-friendly analytics using Plausible.io.
"""

from src.analytics.plausible import (
    PlausibleClient,
    PlausibleEvent,
    Events,
    get_plausible_client,
    get_plausible_script_tag,
    track,
)

__all__ = [
    "PlausibleClient",
    "PlausibleEvent", 
    "Events",
    "get_plausible_client",
    "get_plausible_script_tag",
    "track",
]
