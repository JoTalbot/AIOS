"""Tests for monitoring and health endpoints"""

import pytest
from httpx import ASGITransport, AsyncClient

from aios_core.api.app import create_app


@pytest.mark.asyncio
async def test_health_endpoint():
    app = create_app(auth_required=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


@pytest.mark.asyncio
async def test_metrics_endpoint():
    app = create_app(auth_required=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/metrics")
        assert resp.status_code == 200
        assert "aios_constitution_articles" in resp.text
        assert "aios_memory_items" in resp.text


@pytest.mark.asyncio
async def test_stats_includes_monitoring_fields():
    app = create_app(auth_required=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "constitution_articles" in data
        assert "memory_items" in data
        assert "evolution_proposals" in data
        assert "active_tasks" in data
