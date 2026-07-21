"""Tests for Web UI REST API Endpoints (Milestone 4.2.3)."""

import pytest
from httpx import AsyncClient, ASGITransport
from aios_core.api.app import create_app


@pytest.fixture
def app():
    return create_app(db_path=":memory:", auth_required=False)


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_ui_constitution_endpoint(client):
    resp = await client.get("/api/v1/constitution")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 67
    assert data[0]["number"] == 1


@pytest.mark.asyncio
async def test_ui_safety_endpoint(client):
    resp = await client.get("/api/v1/safety")
    assert resp.status_code == 200
    data = resp.json()
    assert "safety_score" in data
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_ui_knowledge_graph_endpoint(client):
    resp = await client.get("/api/v1/knowledge-graph")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data


@pytest.mark.asyncio
async def test_ui_agents_endpoint(client):
    resp = await client.get("/api/v1/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_ui_models_endpoint(client):
    resp = await client.get("/api/v1/models")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data[0]["name"] == "risk_scorer"
