"""Tests for the NotificationDispatcher."""

from unittest.mock import MagicMock

import pytest

from src.notifications.dispatcher import NotificationDispatcher


class TestDispatcherMultiNotifier:
    def test_dispatches_to_all(self) -> None:
        d = NotificationDispatcher()
        d._notifiers.clear()  # remove auto-registered

        n1 = MagicMock()
        n2 = MagicMock()
        d.register(n1)
        d.register(n2)

        d.dispatch("build.started", "b1", {"key": "val"})

        n1.send.assert_called_once_with("build.started", "b1", {"key": "val"})
        n2.send.assert_called_once_with("build.started", "b1", {"key": "val"})


class TestDispatcherErrorIsolation:
    def test_one_failure_does_not_block_others(self) -> None:
        d = NotificationDispatcher()
        d._notifiers.clear()

        failing = MagicMock()
        failing.send.side_effect = RuntimeError("boom")
        succeeding = MagicMock()

        d.register(failing)
        d.register(succeeding)

        # Should not raise
        d.dispatch("build.completed", "b2", {})

        failing.send.assert_called_once()
        succeeding.send.assert_called_once()


class TestDispatcherAutoRegister:
    def test_empty_when_no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("WEBHOOK_URL", raising=False)
        monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
        d = NotificationDispatcher()
        assert len(d._notifiers) == 0
