"""Unit tests for AIOS v11.19.0 features: REST API routes and Dashboard Server integration."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from aios_core.dashboard import create_dashboard
from aios_core.orchestrator import Orchestrator


@pytest.fixture
def client():
    orch = Orchestrator()
    app = create_dashboard(orch)
    return TestClient(app)


def test_api_substrate_budget_throttle_endpoint(client):
    """Test GET and POST /api/substrate/budget/throttle endpoints."""
    # GET initial status
    resp = client.get("/api/substrate/budget/throttle")
    assert resp.status_code == 200
    data = resp.json()
    assert "auto_throttle_enabled" in data
    assert "throttle_threshold" in data

    # POST configure throttle
    resp2 = client.post("/api/substrate/budget/throttle", json={"enabled": True, "threshold": 0.75})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["auto_throttle_enabled"] is True
    assert data2["throttle_threshold"] == 0.75


def test_api_substrate_policy_autotune_endpoint(client):
    """Test POST /api/substrate/policy/autotune endpoint."""
    resp = client.post("/api/substrate/policy/autotune", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "recommended_policy" in data["recommendation"]


def test_api_memory_health_endpoint(client):
    """Test GET /api/memory/health endpoint."""
    resp = client.get("/api/memory/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "vitality_score" in data
    assert "fragmentation_ratio" in data


def test_api_memory_snapshot_prune_endpoint(client, tmp_path):
    """Test POST /api/memory/snapshot/prune endpoint."""
    snap = tmp_path / "memory.json"
    # Save a live snapshot first
    client.post("/api/memory/snapshot/save", json={"path": str(snap)})

    resp = client.post("/api/memory/snapshot/prune", json={"path": str(snap), "max_age_days": 30.0, "keep_last": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert "pruned_count" in data


def test_api_retention_maintenance_run_endpoint(client):
    """Test POST /api/retention/maintenance/run with confirm guard."""
    # Without confirm: true -> 400
    resp1 = client.post("/api/retention/maintenance/run", json={})
    assert resp1.status_code == 400

    # With confirm: true -> 200
    resp2 = client.post("/api/retention/maintenance/run", json={"confirm": True})
    assert resp2.status_code == 200
    data = resp2.json()
    assert "total_records_purged" in data
