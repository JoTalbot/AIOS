"""Tests for the windowed scheduler report + ?window= endpoint (v11.10.0)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.dashboard import create_dashboard
from aios_core.substrate_convergence import SubstrateConvergenceEngine
from aios_core.substrate_energy_scheduler import EnergyAwareScheduler, RollingEnergyBudget


@pytest.fixture()
def scheduler() -> EnergyAwareScheduler:
    engine = SubstrateConvergenceEngine()
    sched = EnergyAwareScheduler(engine, energy_budget=RollingEnergyBudget(limit=10.0))
    sched.dispatch({"id": "w1", "category": "general", "compute_units": 2})
    sched.dispatch({"id": "w2", "category": "general", "compute_units": 3})
    return sched


def test_report_window_parity_for_recent_dispatches(scheduler):
    full = scheduler.report()
    hour = scheduler.report(window_seconds=3600)
    # All dispatches are fresh: windowed numbers equal the lifetime ones.
    assert hour["dispatches"] == full["dispatches"] == 2
    assert hour["energy_spent_total"] == full["energy_spent_total"]
    assert hour["policy_dispatches"] == full["policy_dispatches"]
    assert full["window_seconds"] is None
    assert hour["window_seconds"] == 3600


def test_report_window_excludes_old_dispatches(scheduler):
    scheduler._dispatches.append(
        {
            "task_id": "ancient",
            "policy": "fallback",
            "scheduling_policy": "min_latency",
            "substrate": "silicon_x86_arm",
            "energy_cost": 0.5,
            "energy_saved": 0.1,
            "timestamp": time.time() - 7200,
        }
    )
    full = scheduler.report()
    assert full["dispatches"] == 3
    assert full["policy_dispatches"]["min_latency"] == 1

    hour = scheduler.report(window_seconds=3600)
    assert hour["dispatches"] == 2  # the 2-hour-old dispatch is out
    assert "min_latency" not in hour["policy_dispatches"]
    assert hour["fallback_dispatches"] == 0
    assert hour["energy_spent_total"] == round(full["energy_spent_total"] - 0.5, 4)
    assert hour["energy_saved_vs_baseline"] == round(full["energy_saved_vs_baseline"] - 0.1, 4)

    wide = scheduler.report(window_seconds=7201)
    assert wide["dispatches"] == 3


def test_report_window_validates(scheduler):
    with pytest.raises(ValueError, match="positive"):
        scheduler.report(window_seconds=0)
    with pytest.raises(ValueError, match="positive"):
        scheduler.report(window_seconds=-60)


# ----------------------------------------------------------------------
# Dashboard endpoint + panel wiring
# ----------------------------------------------------------------------


@pytest.fixture()
def client():
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.10.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None


def test_scheduler_endpoint_window(client):
    client.post(
        "/api/substrate/schedule", json={"id": "e1", "category": "general", "compute_units": 2, "execute": True}
    )
    full = client.get("/api/substrate/scheduler").json()
    assert full["window_seconds"] is None
    assert full["dispatches"] == 1
    hour = client.get("/api/substrate/scheduler?window=3600").json()
    assert hour["window_seconds"] == 3600.0
    assert hour["dispatches"] == 1
    assert hour["energy_spent_total"] == full["energy_spent_total"]


def test_scheduler_endpoint_window_validation(client):
    assert client.get("/api/substrate/scheduler?window=abc").status_code == 400
    assert client.get("/api/substrate/scheduler?window=0").status_code == 400
    assert client.get("/api/substrate/scheduler?window=-5").status_code == 400
    huge = client.get("/api/substrate/scheduler?window=99999999999")
    assert huge.status_code == 200
    assert huge.json()["window_seconds"] == 31_536_000.0  # clamped to one year


def test_substrate_page_has_window_stat(client):
    resp = client.get("/substrate")
    assert "sch-window" in resp.text
    assert "/api/substrate/scheduler?window=3600" in resp.text
