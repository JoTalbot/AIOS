"""Tests for the live Substrate Convergence dashboard (v11.3.0)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.dashboard import create_dashboard


@pytest.fixture()
def client():
    # Fresh convergence engine + energy scheduler for every test (module singletons)
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.7.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None


def test_substrate_page_served(client):
    resp = client.get("/substrate")
    assert resp.status_code == 200
    assert "Substrate Convergence" in resp.text
    assert "/api/substrate/mesh" in resp.text  # live data wiring, not the old mock


def test_substrate_stats_shape(client):
    data = client.get("/api/substrate/stats").json()
    assert data["registered_substrates"] == 5
    assert data["active_substrates"] == 5
    assert data["total_dispatches"] == 0
    assert data["queued_tasks"] == 0
    assert "total_energy_cost" in data
    assert "failover_events" in data


def test_substrate_mesh_all_five_substrates(client):
    mesh = client.get("/api/substrate/mesh").json()["substrates"]
    for substrate in ["quantum_qpu", "photonic_optical", "neuromorphic_snn", "bio_compute", "silicon_x86_arm"]:
        assert substrate in mesh
        info = mesh[substrate]
        assert "latency_base_ms" in info
        assert "efficiency_gflops_per_watt" in info
        assert info["health"] == pytest.approx(1.0)
        assert info["active"] is True


def test_substrate_energy_report(client):
    report = client.get("/api/substrate/energy").json()
    assert report["total_energy_cost"] == 0
    ranking = report["energy_efficiency_ranking"]
    assert ranking[0] == "bio_compute"  # most efficient first


def test_substrate_history_empty_then_populated(client):
    assert client.get("/api/substrate/history").json()["history"] == []

    engine = dashboard_module._get_substrate_engine()
    engine.execute_substrate_task({"id": "task-1", "compute_units": 2, "category": "compute"})
    engine.execute_substrate_task({"id": "task-2", "compute_units": 1, "category": "crypto"})

    history = client.get("/api/substrate/history?limit=10").json()["history"]
    ids = [h["task_id"] for h in history]
    assert ids == ["task-1", "task-2"]
    assert history[0]["energy_cost"] > 0

    stats = client.get("/api/substrate/stats").json()
    assert stats["total_dispatches"] == 2


def test_substrate_history_limit_validation(client):
    engine = dashboard_module._get_substrate_engine()
    for i in range(5):
        engine.execute_substrate_task({"id": f"bulk-{i}", "compute_units": 1})
    history = client.get("/api/substrate/history?limit=3").json()["history"]
    assert len(history) == 3
    # non-numeric limit falls back to default instead of 500-ing
    fallback = client.get("/api/substrate/history?limit=abc")
    assert fallback.status_code == 200


# ------------------------------------------------------------------
# Energy Scheduler panel + report endpoint (v11.7.0)
# ------------------------------------------------------------------


def test_substrate_page_has_scheduler_panel(client):
    resp = client.get("/substrate")
    assert resp.status_code == 200
    assert "v11.13.0" in resp.text
    assert "sch-dispatches" in resp.text
    assert "/api/substrate/scheduler" in resp.text
    assert "/api/substrate/schedule" in resp.text  # plan form wiring


def test_scheduler_report_endpoint(client):
    rep = client.get("/api/substrate/scheduler").json()
    assert rep["dispatches"] == 0
    assert rep["fallback_dispatches"] == 0
    assert rep["energy_spent_total"] == 0
    assert rep["energy_saved_vs_baseline"] == 0
    assert rep["savings_pct"] == 0.0
    # Dashboard scheduler carries a rolling energy budget (100 units / hour)
    budget = rep["energy_budget"]
    assert budget["limit"] == 100.0
    assert budget["remaining"] == pytest.approx(100.0)


def test_scheduler_report_reflects_dispatches(client):
    sched = dashboard_module._get_energy_scheduler()
    sched.dispatch({"id": "r1", "category": "signal", "compute_units": 2})
    rep = client.get("/api/substrate/scheduler").json()
    assert rep["dispatches"] == 1
    assert rep["energy_spent_total"] > 0
    assert rep["energy_budget"]["spent"] > 0
