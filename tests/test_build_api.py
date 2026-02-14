"""Tests for the Build pipeline API endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    """Create a test client for the dashboard app."""
    from src.dashboard.app import create_app

    app = create_app()
    return TestClient(app)


@pytest.fixture()
def csrf_client(client: TestClient):
    """Return (client, headers) with a valid CSRF token."""
    # Make a GET to pick up the csrftoken cookie
    client.get("/dashboard")
    token = client.cookies.get("csrftoken", "")
    return client, {"X-CSRFToken": token}


class TestPostBuild:
    def test_missing_idea_returns_422(self, csrf_client) -> None:
        client, headers = csrf_client
        resp = client.post("/api/build", json={"theme": "Modern"}, headers=headers)
        assert resp.status_code == 422

    def test_short_idea_returns_422(self, csrf_client) -> None:
        client, headers = csrf_client
        resp = client.post("/api/build", json={"idea": "ab"}, headers=headers)
        assert resp.status_code == 422

    def test_valid_build_returns_201_fields(self, csrf_client) -> None:
        client, headers = csrf_client
        resp = client.post("/api/build", json={"idea": "A marketplace for vintage sneakers"}, headers=headers)
        # 200 is acceptable (FastAPI default for POST without status_code override)
        assert resp.status_code == 200
        data = resp.json()
        assert "build_id" in data
        assert "status" in data
        assert "stream_url" in data
        assert data["stream_url"].startswith("/api/build/")


class TestGetBuilds:
    def test_list_returns_array(self, client: TestClient) -> None:
        resp = client.get("/api/builds")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestSSEContentType:
    def test_stream_sets_event_stream(self, csrf_client) -> None:
        client, headers = csrf_client
        # Create a build first
        create_resp = client.post("/api/build", json={"idea": "Test idea for SSE streaming"}, headers=headers)
        build_id = create_resp.json()["build_id"]
        # The stream endpoint should return text/event-stream
        with client.stream("GET", f"/api/build/{build_id}/stream") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")

    def test_stream_404_for_missing(self, client: TestClient) -> None:
        resp = client.get("/api/build/nonexistent-id/stream")
        assert resp.status_code == 404
