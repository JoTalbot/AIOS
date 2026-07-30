"""Tests for engine dispatch analytics + endpoint + panel (v11.7.0)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.dashboard import create_dashboard
from aios_core.substrate_convergence import SubstrateConvergenceEngine


def test_analytics_empty():
    engine = SubstrateConvergenceEngine()
    data = engine.analytics()
    assert data["total_dispatches"] == 0
    assert data["per_substrate"] == {}
    assert data["energy_share_pct"] == {}
    assert data["window_limit"] is None


def test_analytics_aggregates_per_substrate():
    engine = SubstrateConvergenceEngine()
    engine.execute_substrate_task({"id": "a1", "category": "signal", "compute_units": 2})
    engine.execute_substrate_task({"id": "a2", "category": "signal", "compute_units": 1})
    engine.execute_substrate_task({"id": "a3", "category": "compute", "compute_units": 1})

    data = engine.analytics()
    assert data["total_dispatches"] == 3

    photonic = data["per_substrate"]["photonic_optical"]
    assert photonic["dispatches"] == 2
    assert photonic["energy_cost"] == pytest.approx(0.03)
    assert photonic["avg_latency_ms"] == pytest.approx(0.05)

    silicon = data["per_substrate"]["silicon_x86_arm"]
    assert silicon["dispatches"] == 1
    assert silicon["energy_cost"] == pytest.approx(0.1)
    assert silicon["avg_latency_ms"] == pytest.approx(5.0)

    shares = data["energy_share_pct"]
    assert shares["silicon_x86_arm"] > shares["photonic_optical"]
    assert sum(shares.values()) == pytest.approx(100.0)


def test_analytics_window_limit():
    engine = SubstrateConvergenceEngine()
    for i in range(5):
        engine.execute_substrate_task({"id": f"w{i}", "category": "signal", "compute_units": 1})
    engine.execute_substrate_task({"id": "w-silicon", "category": "compute", "compute_units": 1})

    windowed = engine.analytics(limit=1)
    assert windowed["total_dispatches"] == 1
    assert list(windowed["per_substrate"]) == ["silicon_x86_arm"]
    assert windowed["window_limit"] == 1


# ------------------------------------------------------------------
# Dashboard endpoint + page wiring
# ------------------------------------------------------------------


@pytest.fixture()
def client():
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.7.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None


def test_analytics_endpoint_shape(client):
    engine = dashboard_module._get_substrate_engine()
    engine.execute_substrate_task({"id": "e1", "category": "signal", "compute_units": 1})

    data = client.get("/api/substrate/analytics").json()
    assert data["total_dispatches"] == 1
    assert data["per_substrate"]["photonic_optical"]["dispatches"] == 1

    windowed = client.get("/api/substrate/analytics?limit=1").json()
    assert windowed["window_limit"] == 1
    # invalid limit falls back to full history instead of 500-ing
    fallback = client.get("/api/substrate/analytics?limit=abc")
    assert fallback.status_code == 200


def test_substrate_page_has_analytics_panel(client):
    resp = client.get("/substrate")
    assert resp.status_code == 200
    assert "v11.20.0" in resp.text
    assert "/api/substrate/analytics" in resp.text
    assert "analytics-bars" in resp.text
    assert "Dispatch Analytics" in resp.text
