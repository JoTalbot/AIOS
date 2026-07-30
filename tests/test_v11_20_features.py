"""Unit tests for AIOS v11.20.0 features: Developer SDK Client methods."""

from __future__ import annotations

import httpx
import pytest

from aios_core.dashboard import create_dashboard
from aios_core.orchestrator import Orchestrator
from sdk.aios_sdk import AIOSClientSync


@pytest.fixture
def app():
    orch = Orchestrator()
    return create_dashboard(orch)


@pytest.mark.asyncio
async def test_sdk_throttle_and_autotune_methods(app):
    """Test throttle config, configure throttle, and auto_tune_policy endpoints."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as httpx_c:
        res = await httpx_c.get("/api/substrate/budget/throttle")
        assert res.status_code == 200
        assert "auto_throttle_enabled" in res.json()

        res2 = await httpx_c.post("/api/substrate/budget/throttle", json={"enabled": True, "threshold": 0.75})
        assert res2.status_code == 200
        assert res2.json()["auto_throttle_enabled"] is True

        res3 = await httpx_c.post("/api/substrate/policy/autotune", json={})
        assert res3.status_code == 200
        assert "recommended_policy" in res3.json()["recommendation"]


@pytest.mark.asyncio
async def test_sdk_memory_health_and_prune_methods(app, tmp_path):
    """Test memory health and snapshot prune endpoints."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as httpx_c:
        res = await httpx_c.get("/api/memory/health")
        assert res.status_code == 200
        assert "vitality_score" in res.json()

        snap = tmp_path / "memory.json"
        await httpx_c.post("/api/memory/snapshot/save", json={"path": str(snap)})

        res2 = await httpx_c.post(
            "/api/memory/snapshot/prune", json={"path": str(snap), "max_age_days": 14.0, "keep_last": 2}
        )
        assert res2.status_code == 200
        assert "pruned_count" in res2.json()


def test_sdk_sync_wrapper_methods():
    """Test that AIOSClientSync contains all new mirrored methods."""
    sync_c = AIOSClientSync("http://localhost:8000")
    assert hasattr(sync_c, "get_throttle_config")
    assert hasattr(sync_c, "configure_throttle")
    assert hasattr(sync_c, "auto_tune_policy")
    assert hasattr(sync_c, "get_memory_health")
    assert hasattr(sync_c, "prune_snapshots")
    assert hasattr(sync_c, "run_retention_maintenance")
