"""
Notification Dispatcher

Aggregates all configured notifiers and dispatches events, isolating errors
so one notifier failure cannot block others.
"""

import logging
from typing import Any

from .discord import DiscordNotifier
from .webhook import WebhookNotifier

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Fan-out dispatcher for build lifecycle notifications."""

    def __init__(self) -> None:
        self._notifiers: list[WebhookNotifier | DiscordNotifier] = []
        self._auto_register()

    def _auto_register(self) -> None:
        """Register notifiers whose env vars are present."""
        wh = WebhookNotifier()
        if wh.enabled:
            self._notifiers.append(wh)
            logger.info("WebhookNotifier registered")

        dc = DiscordNotifier()
        if dc.enabled:
            self._notifiers.append(dc)
            logger.info("DiscordNotifier registered")

    def register(self, notifier: WebhookNotifier | DiscordNotifier) -> None:
        """Manually register an additional notifier."""
        self._notifiers.append(notifier)

    def dispatch(self, event: str, build_id: str, data: dict[str, Any]) -> None:
        """Send *event* to every registered notifier, isolating failures."""
        for notifier in self._notifiers:
            try:
                notifier.send(event, build_id, data)
            except Exception:
                logger.warning(
                    "Notifier %s failed for event=%s build=%s",
                    type(notifier).__name__,
                    event,
                    build_id,
                    exc_info=True,
                )


# Module-level singleton
dispatcher = NotificationDispatcher()
