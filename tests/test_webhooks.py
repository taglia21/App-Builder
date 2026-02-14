"""Tests for the Webhook notifier."""

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

from src.notifications.webhook import WebhookNotifier


class TestWebhookDisabled:
    def test_noop_when_no_url(self) -> None:
        notifier = WebhookNotifier(webhook_url="", webhook_secret="")
        # Should not raise
        notifier.send("build.started", "b1", {"foo": "bar"})

    def test_enabled_property(self) -> None:
        assert not WebhookNotifier(webhook_url="").enabled
        assert WebhookNotifier(webhook_url="https://example.com/hook").enabled


class TestWebhookSend:
    @patch("src.notifications.webhook.requests.post")
    def test_posts_json(self, mock_post: MagicMock) -> None:
        notifier = WebhookNotifier(webhook_url="https://example.com/hook")
        notifier.send("build.started", "b1", {"idea": "test"})

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["timeout"] == 5
        body = json.loads(call_kwargs.kwargs["data"])
        assert body["event"] == "build.started"
        assert body["build_id"] == "b1"

    @patch("src.notifications.webhook.requests.post")
    def test_hmac_signature(self, mock_post: MagicMock) -> None:
        secret = "supersecret"  # noqa: S105
        notifier = WebhookNotifier(webhook_url="https://example.com/hook", webhook_secret=secret)
        notifier.send("build.completed", "b2", {})

        headers = mock_post.call_args.kwargs["headers"]
        payload = mock_post.call_args.kwargs["data"]
        expected_sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        assert headers["X-Valeric-Signature"] == expected_sig


class TestWebhookTimeout:
    @patch("src.notifications.webhook.requests.post", side_effect=Exception("timeout"))
    def test_swallows_exceptions(self, mock_post: MagicMock) -> None:
        notifier = WebhookNotifier(webhook_url="https://example.com/hook")
        # Must not raise
        notifier.send("build.failed", "b3", {"error": "boom"})
