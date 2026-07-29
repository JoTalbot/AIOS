"""Tests for scheduling policies + AI-manager wiring (v11.7.0)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.dashboard import create_dashboard
from aios_core.substrate_convergence import SubstrateConvergenceEngine
from aios_core.substrate_energy_scheduler import SCHEDULING_POLICIES, EnergyAwareScheduler


@pytest.fixture()
def engine() -> SubstrateConvergenceEngine:
    return SubstrateConvergenceEngine()


def test_policy_validation():
    engine = SubstrateConvergenceEngine()
    with pytest.raises(ValueError, match="unknown scheduling policy"):
        EnergyAwareScheduler(engine, policy="esoteric")
    for name in SCHEDULING_POLICIES:
        EnergyAwareScheduler(engine, policy=name)  # all supported names pass
    scheduler = EnergyAwareScheduler(engine)
    with pytest.raises(ValueError):
        scheduler.plan({"category": "x"}, policy="nope")


def test_min_energy_is_default_and_cheapest(engine):
    scheduler = EnergyAwareScheduler(engine)
    plan = scheduler.plan({"category": "zzz", "compute_units": 1})
    assert plan["policy"] == "min_energy"
    assert plan["selected_substrate"] == "photonic_optical"
    assert "ai_q_value" not in plan  # only emitted for the AI policy


def test_min_latency_picks_fastest_not_cheapest(engine):
    # A deliberately slow-but-cheap substrate splits the two policies.
    engine.register_substrate(
        "cheap_slow",
        latency_base_ms=100.0,
        efficiency_gflops_per_watt=10.0,
        energy_cost_per_unit=0.001,
        capacity=100,
    )
    task = {"category": "zzz", "compute_units": 1}
    energy_first = EnergyAwareScheduler(engine, policy="min_energy").plan(task)
    latency_first = EnergyAwareScheduler(engine, policy="min_latency").plan(task)
    assert energy_first["selected_substrate"] == "cheap_slow"  # 0.001 < 0.01
    assert latency_first["selected_substrate"] == "photonic_optical"  # 0.05ms


def test_balanced_policy_weight_extremes(engine):
    engine.register_substrate(
        "cheap_slow",
        latency_base_ms=100.0,
        efficiency_gflops_per_watt=10.0,
        energy_cost_per_unit=0.001,
        capacity=100,
    )
    task = {"category": "zzz", "compute_units": 1}
    energy_only = EnergyAwareScheduler(engine, policy="balanced", balanced_weights=(1.0, 0.0))
    latency_only = EnergyAwareScheduler(engine, policy="balanced", balanced_weights=(0.0, 1.0))
    assert energy_only.plan(task)["selected_substrate"] == "cheap_slow"
    assert latency_only.plan(task)["selected_substrate"] == "photonic_optical"


def test_ai_optimized_cold_table_falls_back_to_min_energy(engine):
    scheduler = EnergyAwareScheduler(engine, policy="ai_optimized")
    plan = scheduler.plan({"category": "zzz", "compute_units": 1})
    assert plan["selected_substrate"] == "photonic_optical"  # min_energy tie-break
    assert plan["ai_q_value"] == 0.0


def test_ai_optimized_uses_learned_q_values(engine):
    engine.ai_manager.q_table["zzz"] = {
        "quantum_qpu": 9.5,
        "silicon_x86_arm": 4.0,
        "photonic_optical": -1.0,
    }
    scheduler = EnergyAwareScheduler(engine, policy="ai_optimized")
    plan = scheduler.plan({"category": "zzz", "compute_units": 1})
    assert plan["selected_substrate"] == "quantum_qpu"  # argmax Q, not cheapest
    assert plan["ai_q_value"] == pytest.approx(9.5)


def test_dispatch_records_policy_and_report_counts(engine):
    scheduler = EnergyAwareScheduler(engine)  # default min_energy
    result = scheduler.dispatch({"id": "p1", "category": "zzz"}, policy="min_latency")
    assert result["scheduling_policy"] == "min_latency"
    scheduler.dispatch({"id": "p2", "category": "zzz"})  # default policy
    report = scheduler.report()
    assert report["policy"] == "min_energy"
    assert report["policy_dispatches"] == {"min_latency": 1, "min_energy": 1}


def test_ai_learning_loop_after_dispatches(engine):
    # The engine feeds real dispatch outcomes into the AI manager — every
    # scheduler dispatch teaches the Q-table for that category.
    scheduler = EnergyAwareScheduler(engine)
    assert "loop_cat" not in engine.ai_manager.q_table
    for _ in range(3):
        scheduler.dispatch({"id": "loop", "category": "loop_cat", "compute_units": 1})
    q = engine.ai_manager.q_table.get("loop_cat", {})
    assert any(value > 0 for value in q.values())


# ------------------------------------------------------------------
# Dashboard API
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


def test_schedule_api_policy_param(client):
    plan = client.post(
        "/api/substrate/schedule",
        json={"category": "zzz", "compute_units": 1, "policy": "min_latency"},
    ).json()
    assert plan["policy"] == "min_latency"
    assert plan["selected_substrate"] == "photonic_optical"


def test_schedule_api_rejects_unknown_policy(client):
    resp = client.post("/api/substrate/schedule", json={"category": "zzz", "policy": "nope"})
    assert resp.status_code == 400
    assert "unknown scheduling policy" in resp.json()["error"]


def test_scheduler_report_exposes_policy_fields(client):
    rep = client.get("/api/substrate/scheduler").json()
    assert rep["policy"] == "min_energy"
    assert rep["policy_dispatches"] == {}
