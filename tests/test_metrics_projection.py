"""Tests for the Prometheus policy-projection series (v11.13.0)."""

from __future__ import annotations

import re
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.dashboard import create_dashboard
from aios_core.metrics_export import render_prometheus
from aios_core.substrate_convergence import SubstrateConvergenceEngine
from aios_core.substrate_energy_scheduler import (
    SCHEDULING_POLICIES,
    EnergyAwareScheduler,
    RollingEnergyBudget,
)


@pytest.fixture()
def systems():
    engine = SubstrateConvergenceEngine()
    engine.register_substrate(
        "cheap_slow",
        latency_base_ms=100.0,
        efficiency_gflops_per_watt=10.0,
        energy_cost_per_unit=0.001,
        capacity=100,
    )
    engine.register_substrate(
        "fast_pricey",
        latency_base_ms=1.0,
        efficiency_gflops_per_watt=5.0,
        energy_cost_per_unit=0.5,
        capacity=100,
    )
    for i in range(3):
        engine.execute_substrate_task({"id": f"m{i}", "category": "general", "compute_units": 4})
    scheduler = EnergyAwareScheduler(
        engine,
        energy_budget=RollingEnergyBudget(limit=100.0, window_seconds=3600.0),
    )
    return engine, scheduler


def test_projection_series_rendered_for_all_policies(systems):
    engine, scheduler = systems
    text = render_prometheus(engine=engine, scheduler=scheduler, version="x", policy_projection_records=100)
    assert "aios_policy_projection_tasks 3" in text
    for name in SCHEDULING_POLICIES:
        assert re.search(rf'^aios_policy_projection_energy\{{policy="{name}"\}} [0-9.]+$', text, re.M)
        assert re.search(rf'^aios_policy_projection_delta_vs_reference\{{policy="{name}"\}} -?[0-9.]+$', text, re.M)
        assert re.search(rf'^aios_policy_projection_recommended\{{policy="{name}"\}} [01]$', text, re.M)


def test_projection_exactly_one_recommended(systems):
    engine, scheduler = systems
    text = render_prometheus(engine=engine, scheduler=scheduler, version="x", policy_projection_records=100)
    winners = re.findall(r"^aios_policy_projection_recommended\{[^}]*\} 1$", text, re.M)
    assert len(winners) == 1


def test_projection_reference_delta_is_zero(systems):
    engine, scheduler = systems
    reference = scheduler.policy  # default policy is the compare reference
    text = render_prometheus(engine=engine, scheduler=scheduler, version="x", policy_projection_records=100)
    assert f'aios_policy_projection_delta_vs_reference{{policy="{reference}"}} 0' in text


def test_projection_empty_history_omits_block():
    engine = SubstrateConvergenceEngine()
    engine.register_substrate("silicon", 5.0, 10.0, 0.1, 100)
    scheduler = EnergyAwareScheduler(engine)
    text = render_prometheus(engine=engine, scheduler=scheduler, version="x", policy_projection_records=100)
    assert "aios_policy_projection" not in text


def test_projection_disabled_by_default(systems):
    engine, scheduler = systems
    text = render_prometheus(engine=engine, scheduler=scheduler, version="x")
    assert "aios_policy_projection" not in text


def test_projection_unknown_substrate_falls_back_to_one_unit(systems):
    engine, scheduler = systems
    engine.dispatch_history.append(
        {"task_id": "ghost", "selected_substrate": "no_such_substrate", "energy_cost": 99.0, "timestamp": 1.0}
    )
    # Must not raise; unknown records are reconstructed with 1 compute unit.
    text = render_prometheus(engine=engine, scheduler=scheduler, version="x", policy_projection_records=100)
    assert "aios_policy_projection_tasks 4" in text


@pytest.fixture()
def client():
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.13.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None


def test_metrics_endpoint_includes_projection_series(client):
    for i in range(2):
        resp = client.post(
            "/api/substrate/schedule",
            json={"id": f"proj-{i}", "category": "general", "compute_units": 2, "execute": True},
        )
        assert resp.status_code == 200
    body = client.get("/api/metrics").text
    assert 'aios_info{version="11.13.0"} 1' in body
    assert "aios_policy_projection_tasks 2" in body
    assert re.search(r'^aios_policy_projection_energy\{policy="min_energy"\} [0-9.]+$', body, re.M)
    winners = re.findall(r"^aios_policy_projection_recommended\{[^}]*\} 1$", body, re.M)
    assert len(winners) == 1
