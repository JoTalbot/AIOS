"""Tests for the Energy-Aware Substrate Scheduler (v11.4.0)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.dashboard import create_dashboard
from aios_core.substrate_convergence import SubstrateConvergenceEngine
from aios_core.substrate_energy_scheduler import EnergyAwareScheduler, RollingEnergyBudget

# ------------------------------------------------------------------
# RollingEnergyBudget
# ------------------------------------------------------------------


def test_budget_validation():
    with pytest.raises(ValueError):
        RollingEnergyBudget(limit=0)
    with pytest.raises(ValueError):
        RollingEnergyBudget(limit=-5)
    with pytest.raises(ValueError):
        RollingEnergyBudget(limit=10, window_seconds=0)


def test_budget_spend_and_remaining():
    budget = RollingEnergyBudget(limit=10.0, window_seconds=3600)
    assert budget.remaining() == pytest.approx(10.0)
    assert budget.can_afford(10.0)
    budget.record(4.0)
    assert budget.spent() == pytest.approx(4.0)
    assert budget.remaining() == pytest.approx(6.0)
    assert not budget.can_afford(7.0)
    assert budget.can_afford(6.0)
    # Overspending is prevented by can_afford checks upstream, but the
    # budget itself must stay consistent when recorded anyway.
    budget.record(7.0)
    assert budget.remaining() == pytest.approx(0.0)


def test_budget_window_prune():
    budget = RollingEnergyBudget(limit=10.0, window_seconds=60.0)
    # Spend "outside" the window must be pruned on next query
    budget._spends.append((time.time() - 3600, 8.0))
    budget.record(2.0)
    assert budget.spent() == pytest.approx(2.0)
    assert budget.remaining() == pytest.approx(8.0)
    d = budget.to_dict()
    assert d["limit"] == 10.0
    assert d["spent"] == pytest.approx(2.0)


# ------------------------------------------------------------------
# Scheduler plans
# ------------------------------------------------------------------


@pytest.fixture()
def engine() -> SubstrateConvergenceEngine:
    return SubstrateConvergenceEngine()


def test_candidates_affinity_narrows_pool(engine):
    scheduler = EnergyAwareScheduler(engine)
    cands = scheduler.candidates({"category": "signal", "compute_units": 1})
    assert [c["substrate"] for c in cands] == ["photonic_optical"]
    assert cands[0]["expected_energy"] == pytest.approx(0.01)


def test_candidates_unknown_category_all_active(engine):
    scheduler = EnergyAwareScheduler(engine)
    cands = scheduler.candidates({"category": "zzz-unknown", "compute_units": 2})
    assert len(cands) == 5
    photonic = next(c for c in cands if c["substrate"] == "photonic_optical")
    assert photonic["expected_energy"] == pytest.approx(0.02)


def test_plan_picks_cheapest_energy(engine):
    scheduler = EnergyAwareScheduler(engine)
    plan = scheduler.plan({"id": "t1", "category": "zzz-unknown", "compute_units": 1})
    assert plan["selected_substrate"] == "photonic_optical"  # 0.01 cheapest
    assert plan["constraint_violation"] is False
    # Engine baseline for unknown category is bio_compute (max efficiency),
    # so the policy saves 0.01 energy units per compute unit.
    assert plan["baseline_substrate"] == "bio_compute"
    assert plan["expected_savings"] == pytest.approx(0.01)


def test_plan_matches_engine_on_affinity_tasks(engine):
    scheduler = EnergyAwareScheduler(engine)
    plan = scheduler.plan({"id": "t2", "category": "signal", "compute_units": 1})
    assert plan["selected_substrate"] == plan["baseline_substrate"] == "photonic_optical"
    assert plan["expected_savings"] == pytest.approx(0.0)


def test_plan_latency_budget_filters(engine):
    scheduler = EnergyAwareScheduler(engine, latency_budget_ms=0.06)
    plan = scheduler.plan({"id": "t3", "category": "zzz-unknown", "compute_units": 1})
    assert plan["selected_substrate"] == "photonic_optical"  # only one within 0.06 ms
    assert plan["excluded_by_latency_budget"] == 4
    assert plan["constraint_violation"] is False


def test_plan_latency_budget_no_candidates(engine):
    scheduler = EnergyAwareScheduler(engine, latency_budget_ms=0.01)
    plan = scheduler.plan({"id": "t4", "category": "zzz-unknown", "compute_units": 1})
    assert plan["selected_substrate"] is None
    assert plan["constraint_violation"] is True
    assert "no_substrate_within_constraints" in plan["violations"]


def test_plan_energy_budget_exceeded(engine):
    budget = RollingEnergyBudget(limit=0.005, window_seconds=3600)
    scheduler = EnergyAwareScheduler(engine, energy_budget=budget)
    plan = scheduler.plan({"id": "t5", "category": "zzz-unknown", "compute_units": 1})
    assert plan["constraint_violation"] is True
    assert "energy_budget_exceeded" in plan["violations"]


def test_unhealthy_substrate_excluded(engine):
    engine.update_substrate_health("photonic_optical", 0.1)  # auto-deactivates
    scheduler = EnergyAwareScheduler(engine)
    cands = scheduler.candidates({"category": "signal"})
    assert all(c["substrate"] != "photonic_optical" for c in cands)
    # With photonic gone, bio_compute is now the cheapest active substrate
    plan = scheduler.plan({"id": "t6", "category": "signal"})
    assert plan["selected_substrate"] == "bio_compute"


# ------------------------------------------------------------------
# Dispatch + reporting
# ------------------------------------------------------------------


def test_dispatch_energy_aware_and_savings(engine):
    scheduler = EnergyAwareScheduler(engine)
    result = scheduler.dispatch({"id": "d1", "category": "zzz-unknown", "compute_units": 2})
    assert result["policy"] == "energy_aware"
    assert result["selected_substrate"] == "photonic_optical"
    assert result["energy_cost"] == pytest.approx(0.02)
    # baseline bio_compute: 2 * 0.02 = 0.04 -> savings 0.02
    assert result["energy_saved_vs_baseline"] == pytest.approx(0.02)

    report = scheduler.report()
    assert report["dispatches"] == 1
    assert report["fallback_dispatches"] == 0
    assert report["energy_spent_total"] == pytest.approx(0.02)
    assert report["energy_saved_vs_baseline"] == pytest.approx(0.02)
    assert report["savings_pct"] == pytest.approx(50.0)
    # engine recorded the dispatch too
    assert len(engine.dispatch_history) == 1


def test_dispatch_fallback_on_violation(engine):
    scheduler = EnergyAwareScheduler(engine, latency_budget_ms=0.01)
    result = scheduler.dispatch({"id": "d2", "category": "compute", "compute_units": 1})
    assert result["policy"] == "fallback"
    assert result["violations"]
    assert result["selected_substrate"] is not None  # engine still executed it
    assert result["energy_saved_vs_baseline"] == pytest.approx(0.0)
    assert scheduler.report()["fallback_dispatches"] == 1


def test_dispatch_records_budget(engine):
    budget = RollingEnergyBudget(limit=100.0)
    scheduler = EnergyAwareScheduler(engine, energy_budget=budget)
    scheduler.dispatch({"id": "d3", "category": "zzz-unknown", "compute_units": 3})
    assert budget.spent() == pytest.approx(0.03)
    report = scheduler.report()
    assert report["energy_budget"]["spent"] == pytest.approx(0.03)


def test_report_empty(engine):
    scheduler = EnergyAwareScheduler(engine, latency_budget_ms=5.0)
    report = scheduler.report()
    assert report["dispatches"] == 0
    assert report["savings_pct"] == 0.0
    assert report["latency_budget_ms"] == 5.0
    assert report["energy_budget"] is None


# ------------------------------------------------------------------
# Dashboard API (/api/substrate/schedule)
# ------------------------------------------------------------------


@pytest.fixture()
def client():
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.4.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None


def test_schedule_api_dry_run_plan(client):
    resp = client.post("/api/substrate/schedule", json={"id": "api-1", "category": "zzz", "compute_units": 1})
    assert resp.status_code == 200
    plan = resp.json()
    assert plan["selected_substrate"] == "photonic_optical"
    assert plan["constraint_violation"] is False
    assert "scheduler_report" in plan
    # Dry run must NOT execute anything
    assert plan["scheduler_report"]["dispatches"] == 0
    stats = client.get("/api/substrate/stats").json()
    assert stats["total_dispatches"] == 0


def test_schedule_api_execute_dispatches(client):
    resp = client.post(
        "/api/substrate/schedule",
        json={"id": "api-2", "category": "zzz", "compute_units": 1, "execute": True},
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["policy"] == "energy_aware"
    assert result["selected_substrate"] == "photonic_optical"
    assert client.get("/api/substrate/stats").json()["total_dispatches"] == 1

    # Second plan reflects the recorded dispatch in scheduler_report
    plan = client.post("/api/substrate/schedule", json={"category": "compute"}).json()
    assert plan["scheduler_report"]["dispatches"] == 1


def test_schedule_api_rejects_invalid_body(client):
    resp = client.post("/api/substrate/schedule", content=b"not json at all")
    assert resp.status_code == 400
    resp2 = client.post("/api/substrate/schedule", json=["a", "list"])
    assert resp2.status_code == 400
