"""
Webhook Notifier

Sends build lifecycle events to an external URL with HMAC-SHA256 signing.
Always a no-op when WEBHOOK_URL is not configured.
"""

import hashlib
import hmac
import json
import logging
import os
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


class WebhookNotifier:
    """POST JSON events to a configured webhook URL with HMAC signing."""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        webhook_secret: Optional[str] = None,
    ) -> None:
        self.webhook_url = webhook_url or os.environ.get("WEBHOOK_URL", "")
        self.webhook_secret = webhook_secret or os.environ.get("WEBHOOK_SECRET", "")

    @property
    def enabled(self) -> bool:
        return bool(self.webhook_url)

    def send(self, event: str, build_id: str, data: dict[str, Any]) -> None:
        """Send a webhook notification. No-op if unconfigured.

        Args:
            event: Event name, e.g. ``build.started``.
            build_id: Associated build identifier.
            data: Arbitrary payload dict.
        """
        if not self.enabled:
            return

        payload = json.dumps(
            {"event": event, "build_id": build_id, "data": data},
            default=str,
        )

        headers: dict[str, str] = {"Content-Type": "application/json"}

        if self.webhook_secret:
            signature = hmac.new(
                self.webhook_secret.encode(),
                payload.encode(),
                hashlib.sha256,
            ).hexdigest()
            headers["X-Valeric-Signature"] = signature

        try:
            requests.post(
                self.webhook_url,
                data=payload,
                headers=headers,
                timeout=5,
            )
        except Exception:
            logger.debug("Webhook delivery failed for event=%s build=%s", event, build_id, exc_info=True)
