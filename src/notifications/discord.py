"""
Discord Notifier

Sends build completion/failure embeds to a Discord webhook.
Always a no-op when DISCORD_WEBHOOK_URL is not configured.
"""

import logging
import os
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

# Discord embed colour constants (decimal)
_COLOR_SUCCESS = 0x22C55E  # green
_COLOR_FAILURE = 0xEF4444  # red


class DiscordNotifier:
    """Post rich embeds to a Discord webhook on build.completed / build.failed."""

    def __init__(self, webhook_url: Optional[str] = None) -> None:
        self.webhook_url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL", "")

    @property
    def enabled(self) -> bool:
        return bool(self.webhook_url)

    def send(self, event: str, build_id: str, data: dict[str, Any]) -> None:
        """Send a Discord embed. Only fires for ``build.completed`` and ``build.failed``.

        Args:
            event: Event name.
            build_id: Associated build identifier.
            data: Payload dict (idea, provider, duration, error, etc.).
        """
        if not self.enabled:
            return

        if event not in ("build.completed", "build.failed"):
            return

        is_success = event == "build.completed"
        color = _COLOR_SUCCESS if is_success else _COLOR_FAILURE
        title = "Build Completed" if is_success else "Build Failed"

        fields = [
            {"name": "Build ID", "value": f"`{build_id}`", "inline": True},
        ]
        if data.get("idea"):
            fields.append({"name": "Idea", "value": str(data["idea"])[:200], "inline": False})
        if data.get("provider"):
            fields.append({"name": "Provider", "value": str(data["provider"]), "inline": True})
        if data.get("duration"):
            fields.append({"name": "Duration", "value": str(data["duration"]), "inline": True})
        if data.get("error"):
            fields.append({"name": "Error", "value": str(data["error"])[:500], "inline": False})

        payload = {
            "embeds": [
                {
                    "title": title,
                    "color": color,
                    "fields": fields,
                }
            ]
        }

        try:
            requests.post(
                self.webhook_url,
                json=payload,
                timeout=5,
            )
        except Exception:
            logger.debug("Discord notification failed for event=%s build=%s", event, build_id, exc_info=True)
