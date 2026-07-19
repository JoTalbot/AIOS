"""Regression tests for API authentication, authorization and shared runtime state."""
import pytest
from httpx import ASGITransport, AsyncClient

from aios_core.api.app import create_app


@pytest.mark.asyncio
async def test_api_fails_closed_without_configured_keys():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/health")).status_code == 200
        response = await client.get("/api/v1/stats")
        assert response.status_code == 503


@pytest.mark.asyncio
async def test_role_guard_and_rest_mcp_share_database():
    keys = {
        "viewer-key": {"subject": "viewer", "roles": ["viewer"]},
        "writer-key": {"subject": "writer", "roles": ["writer"]},
    }
    app = create_app(api_keys=keys)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        viewer = {"Authorization": "Bearer viewer-key"}
        writer = {"Authorization": "Bearer writer-key"}
        assert (await client.post("/api/v1/memory", json={"content": {"a": 1}}, headers=viewer)).status_code == 403
        saved = await client.post("/api/v1/memory", json={"content": {"a": 1}}, headers=writer)
        assert saved.status_code == 201
        rpc = await client.post("/rpc", json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "aios_memory_search", "arguments": {"query": "a"}},
        }, headers=writer)
        assert rpc.status_code == 200
        assert '"count": 1' in rpc.json()["result"]["content"][0]["text"]


@pytest.mark.asyncio
async def test_personal_memory_is_isolated_by_authenticated_subject():
    keys = {
        "alice-key": {"subject": "alice", "roles": ["writer"]},
        "bob-key": {"subject": "bob", "roles": ["writer"]},
    }
    app = create_app(api_keys=keys)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        alice = {"Authorization": "Bearer alice-key"}
        bob = {"Authorization": "Bearer bob-key"}
        saved = await client.post("/api/v1/memory", json={
            "content": {"private": "alice only"}, "category": "personal"
        }, headers=alice)
        assert saved.status_code == 201
        item_id = saved.json()["id"]
        assert (await client.get(f"/api/v1/memory/{item_id}", headers=bob)).status_code == 404
        result = await client.get("/api/v1/memory?category=personal", headers=bob)
        assert result.json()["count"] == 0
        assert (await client.get(f"/api/v1/memory/{item_id}", headers=alice)).status_code == 200


@pytest.mark.asyncio
async def test_approver_role_is_required_for_approval_actions():
    keys = {
        "writer-key": {"subject": "writer", "roles": ["writer"]},
        "approver-key": {"subject": "reviewer", "roles": ["approver"]},
    }
    app = create_app(api_keys=keys)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        writer = {"Authorization": "Bearer writer-key"}
        result = await client.post("/api/v1/approvals/not-a-real-id/approve", headers=writer)
        assert result.status_code == 403
        result = await client.post("/api/v1/approvals/not-a-real-id/approve", headers={"Authorization": "Bearer approver-key"})
        assert result.status_code == 404
