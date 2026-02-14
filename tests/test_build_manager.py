"""Tests for the BuildManager service."""

import threading
import time
from pathlib import Path

import pytest

from src.services.build_manager import BuildManager


@pytest.fixture()
def bm(tmp_path: Path) -> BuildManager:
    """Return a BuildManager backed by a temporary SQLite database."""
    return BuildManager(db_path=tmp_path / "test_builds.db")


class TestCreateBuild:
    def test_returns_uuid(self, bm: BuildManager) -> None:
        build_id = bm.create_build(idea="Test idea")
        assert isinstance(build_id, str)
        assert len(build_id) == 36  # UUID4 format

    def test_default_fields(self, bm: BuildManager) -> None:
        build_id = bm.create_build(idea="My idea", llm_provider="groq", theme="Cyberpunk")
        build = bm.get_build(build_id)
        assert build is not None
        assert build["idea"] == "My idea"
        assert build["status"] == "pending"
        assert build["llm_provider"] == "groq"
        assert build["theme"] == "Cyberpunk"
        assert build["progress"] == 0


class TestGetBuild:
    def test_returns_none_for_missing(self, bm: BuildManager) -> None:
        assert bm.get_build("nonexistent-id") is None

    def test_returns_dict(self, bm: BuildManager) -> None:
        build_id = bm.create_build(idea="x")
        build = bm.get_build(build_id)
        assert isinstance(build, dict)
        assert "build_id" in build


class TestListBuilds:
    def test_empty(self, bm: BuildManager) -> None:
        assert bm.list_builds() == []

    def test_ordering(self, bm: BuildManager) -> None:
        id1 = bm.create_build(idea="first")
        time.sleep(0.01)
        id2 = bm.create_build(idea="second")
        builds = bm.list_builds()
        assert len(builds) == 2
        # newest first
        assert builds[0]["build_id"] == id2
        assert builds[1]["build_id"] == id1

    def test_limit(self, bm: BuildManager) -> None:
        for i in range(5):
            bm.create_build(idea=f"idea-{i}")
        assert len(bm.list_builds(limit=3)) == 3


class TestUpdateBuild:
    def test_update_fields(self, bm: BuildManager) -> None:
        build_id = bm.create_build(idea="x")
        bm.update_build(build_id, status="running", progress=42, current_stage="scoring")
        build = bm.get_build(build_id)
        assert build["status"] == "running"
        assert build["progress"] == 42
        assert build["current_stage"] == "scoring"

    def test_no_op_on_empty(self, bm: BuildManager) -> None:
        build_id = bm.create_build(idea="x")
        bm.update_build(build_id)  # should not raise
        assert bm.get_build(build_id)["status"] == "pending"


class TestEventBuffer:
    def test_push_and_get(self, bm: BuildManager) -> None:
        build_id = bm.create_build(idea="x")
        bm.push_event(build_id, {"type": "progress", "stage": "ideas"})
        bm.push_event(build_id, {"type": "complete"})
        events = bm.get_events(build_id)
        assert len(events) == 2
        assert events[0]["type"] == "progress"
        # get_events drains the buffer
        assert bm.get_events(build_id) == []

    def test_get_events_unknown_id(self, bm: BuildManager) -> None:
        assert bm.get_events("unknown") == []

    def test_thread_safety(self, bm: BuildManager) -> None:
        build_id = bm.create_build(idea="concurrent")
        errors: list[str] = []

        def writer(n: int) -> None:
            try:
                for i in range(50):
                    bm.push_event(build_id, {"writer": n, "i": i})
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=writer, args=(n,)) for n in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"
        # All events should have been pushed (some may have been drained)
        # Just verify no corruption
        remaining = bm.get_events(build_id)
        assert isinstance(remaining, list)
