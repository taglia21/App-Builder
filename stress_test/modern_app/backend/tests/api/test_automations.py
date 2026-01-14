"""Automation CRUD tests."""

import pytest
from app.main import app
from httpx import AsyncClient


@pytest.fixture
async def auth_headers():
    """Get authentication headers."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={"email": "crud_test@example.com", "password": "testpassword123"},
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "crud_test@example.com", "password": "testpassword123"},
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_automation(auth_headers):
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/automations/", json={"name": "test"}, headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data


@pytest.mark.asyncio
async def test_list_automations(auth_headers):
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/automations/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
