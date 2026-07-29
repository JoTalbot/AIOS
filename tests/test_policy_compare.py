"""Tests for the policy A/B comparison matrix + endpoint (v11.12.0)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.dashboard import create_dashboard
from aios_core.substrate_convergence import SubstrateConvergenceEngine
from aios_core.substrate_energy_scheduler import SCHEDULING_POLICIES, EnergyAwareScheduler


@pytest.fixture()
def scheduler() -> EnergyAwareScheduler:
    engine = SubstrateConvergenceEngine()
    # Deliberately cheapest-but-slowest: splits min_energy from min_latency.
    engine.register_substrate(
        "cheap_slow",
        latency_base_ms=100.0,
        efficiency_gflops_per_watt=10.0,
        energy_cost_per_unit=0.001,
        capacity=100,
    )
    return EnergyAwareScheduler(engine)


_TASKS = [{"id": f"m{i}", "category": "zzz", "compute_units": 100} for i in range(2)]


def test_compare_matrix_across_all_policies(scheduler):
    report = scheduler.compare_policies(_TASKS)
    assert report["tasks_total"] == 2
    assert report["policies"] == list(SCHEDULING_POLICIES)
    assert report["reference_policy"] == "min_energy"
    matrix = report["matrix"]
    assert set(matrix) == set(SCHEDULING_POLICIES)
    # min_energy and a cold-ai policy pick the cheap substrate; the
    # latency-driven policies pick photonic.
    assert set(matrix["min_energy"]["substrate_choices"]) == {"cheap_slow"}
    assert set(matrix["ai_optimized"]["substrate_choices"]) == {"cheap_slow"}
    assert set(matrix["min_latency"]["substrate_choices"]) == {"photonic_optical"}
    assert matrix["min_energy"]["projected_energy"] == 0.2  # 2 tasks * 100 units * 0.001
    assert matrix["min_latency"]["projected_energy"] == 2.0  # 2 tasks * 100 units * 0.01
    # Deltas vs reference (min_energy).
    assert matrix["min_energy"]["energy_delta_vs_reference"] == 0.0
    assert matrix["min_latency"]["energy_delta_vs_reference"] == 1.8
    assert matrix["min_energy"]["choice_overlap_vs_reference_pct"] == 100.0
    assert matrix["min_latency"]["choice_overlap_vs_reference_pct"] == 0.0
    # Recommended: cheapest; reference wins the tie with the cold AI policy.
    assert report["recommended_policy"] == "min_energy"


def test_compare_subset_and_reference(scheduler):
    report = scheduler.compare_policies(_TASKS, policies=["min_latency", "balanced"], reference_policy="balanced")
    assert report["policies"] == ["min_latency", "balanced"]
    assert report["reference_policy"] == "balanced"
    assert report["matrix"]["balanced"]["energy_delta_vs_reference"] == 0.0


def test_compare_validation(scheduler):
    with pytest.raises(ValueError, match="non-empty"):
        scheduler.compare_policies(_TASKS, policies=[])
    with pytest.raises(ValueError, match="list of policy names"):
        scheduler.compare_policies(_TASKS, policies="min_energy")
    with pytest.raises(ValueError, match="unknown scheduling policy"):
        scheduler.compare_policies(_TASKS, policies=["min_energy", "voodoo"])
    with pytest.raises(ValueError, match="one of the compared policies"):
        scheduler.compare_policies(_TASKS, policies=["min_latency"], reference_policy="min_energy")
    with pytest.raises(ValueError, match="list"):
        scheduler.compare_policies("nope")


def test_compare_is_a_dry_run(scheduler):
    scheduler.compare_policies(_TASKS)
    assert scheduler.report()["dispatches"] == 0
    assert scheduler.engine.stats()["total_dispatches"] == 0


# ----------------------------------------------------------------------
# Dashboard endpoint + panel wiring
# ----------------------------------------------------------------------


@pytest.fixture()
def client():
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.12.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None


def test_compare_endpoint_shape(client):
    resp = client.post(
        "/api/substrate/compare",
        json={"tasks": [{"id": "c1", "category": "general", "compute_units": 5}]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tasks_total"] == 1
    assert len(data["matrix"]) == 4
    for name in SCHEDULING_POLICIES:
        row = data["matrix"][name]
        # category general -> only silicon is a candidate for every policy.
        assert row["substrate_choices"] == ["silicon_x86_arm"]
        assert row["choice_overlap_vs_reference_pct"] == 100.0
    assert client.get("/api/substrate/scheduler").json()["dispatches"] == 0


def test_compare_endpoint_validation(client):
    assert client.post("/api/substrate/compare", json={}).status_code == 400
    assert client.post("/api/substrate/compare", json={"tasks": [], "policies": "x"}).status_code == 400
    assert client.post("/api/substrate/compare", json={"tasks": [], "policies": []}).status_code == 400
    assert client.post("/api/substrate/compare", json={"tasks": [], "policies": ["zzz"]}).status_code == 400
    assert client.post("/api/substrate/compare", json={"tasks": [], "reference": 1}).status_code == 400
    bad = client.post("/api/substrate/compare", content="[9]", headers={"Content-Type": "application/json"})
    assert bad.status_code == 400
    ok = client.post(
        "/api/substrate/compare",
        json={"tasks": [{"compute_units": 1}], "policies": ["min_latency", "min_energy"], "reference": "min_latency"},
    )
    assert ok.status_code == 200
    assert ok.json()["reference_policy"] == "min_latency"


def test_substrate_page_has_compare_button(client):
    resp = client.get("/substrate")
    assert "/api/substrate/compare" in resp.text
    assert "runCompare" in resp.text
    assert "compare-result" in resp.text
