"""Tests for the Discord notifier."""

from unittest.mock import MagicMock, patch

from src.notifications.discord import DiscordNotifier


class TestDiscordDisabled:
    def test_noop_when_no_url(self) -> None:
        notifier = DiscordNotifier(webhook_url="")
        notifier.send("build.completed", "b1", {})

    def test_enabled_property(self) -> None:
        assert not DiscordNotifier(webhook_url="").enabled
        assert DiscordNotifier(webhook_url="https://discord.com/api/webhooks/x/y").enabled


class TestDiscordIgnoresOtherEvents:
    @patch("src.notifications.discord.requests.post")
    def test_ignores_stage_changed(self, mock_post: MagicMock) -> None:
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/x/y")
        notifier.send("build.stage_changed", "b1", {})
        mock_post.assert_not_called()

    @patch("src.notifications.discord.requests.post")
    def test_ignores_started(self, mock_post: MagicMock) -> None:
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/x/y")
        notifier.send("build.started", "b1", {})
        mock_post.assert_not_called()


class TestDiscordEmbed:
    @patch("src.notifications.discord.requests.post")
    def test_completed_embed_format(self, mock_post: MagicMock) -> None:
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/x/y")
        notifier.send("build.completed", "b1", {"idea": "My SaaS", "provider": "groq", "duration": "2m 30s"})

        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs["json"]
        embed = payload["embeds"][0]
        assert embed["title"] == "Build Completed"
        assert embed["color"] == 0x22C55E
        field_names = [f["name"] for f in embed["fields"]]
        assert "Build ID" in field_names
        assert "Idea" in field_names

    @patch("src.notifications.discord.requests.post")
    def test_failed_embed(self, mock_post: MagicMock) -> None:
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/x/y")
        notifier.send("build.failed", "b2", {"error": "LLM timeout"})

        embed = mock_post.call_args.kwargs["json"]["embeds"][0]
        assert embed["title"] == "Build Failed"
        assert embed["color"] == 0xEF4444


class TestDiscordTimeout:
    @patch("src.notifications.discord.requests.post", side_effect=Exception("connection refused"))
    def test_swallows_exceptions(self, mock_post: MagicMock) -> None:
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/x/y")
        notifier.send("build.completed", "b3", {})
