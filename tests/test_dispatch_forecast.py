"""Tests for batch dispatch forecasting + its dashboard endpoint (v11.8.0)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.dashboard import create_dashboard
from aios_core.substrate_convergence import SubstrateConvergenceEngine
from aios_core.substrate_energy_scheduler import EnergyAwareScheduler, RollingEnergyBudget


@pytest.fixture()
def engine() -> SubstrateConvergenceEngine:
    return SubstrateConvergenceEngine()


@pytest.fixture()
def scheduler(engine) -> EnergyAwareScheduler:
    return EnergyAwareScheduler(engine, energy_budget=RollingEnergyBudget(limit=1.0, window_seconds=3600.0))


def test_forecast_does_not_mutate_state(scheduler):
    before_report = scheduler.report()
    out = scheduler.forecast([{"id": "t1", "category": "general", "compute_units": 2}])
    assert out["tasks_total"] == 1
    assert out["tasks_affordable"] == 1
    # Nothing executed, recorded or budgeted.
    assert scheduler.report() == before_report
    assert scheduler.energy_budget.spent() == 0.0
    assert scheduler.engine.stats()["total_dispatches"] == 0


def test_forecast_projects_cumulative_energy(scheduler):
    out = scheduler.forecast(
        [
            {"id": "a", "category": "zzz", "compute_units": 5},
            {"id": "b", "category": "zzz", "compute_units": 7},
        ]
    )
    first, second = out["plans"]
    assert first["index"] == 0 and second["index"] == 1
    assert first["expected_energy"] > 0
    assert first["cumulative_energy"] == first["expected_energy"]
    assert second["cumulative_energy"] == round(first["expected_energy"] + second["expected_energy"], 6)
    assert out["projected_energy"] == second["cumulative_energy"]
    assert out["tasks_affordable"] == 2
    assert out["window_limit"] == 1.0
    assert out["window_spent_now"] == 0.0
    assert out["window_remaining_after"] == round(1.0 - out["projected_energy"], 6)
    assert first["violations"] == []
    assert first["selected_substrate"] == "photonic_optical"  # cheapest for unknown category


def test_forecast_flags_projected_budget_exceed(scheduler):
    # Task size tuned so exactly int(limit // per_task) batches fit the window.
    unit_energy = scheduler.plan({"id": "probe", "category": "zzz", "compute_units": 1})["expected_energy"]
    per_task_units = 45  # 45 * 0.01 = 0.45 -> two fit, the third overshoots 1.0
    per_task_energy = round(per_task_units * unit_energy, 6)
    expected_affordable = int(1.0 // per_task_energy)
    tasks = [{"id": f"t{i}", "category": "zzz", "compute_units": per_task_units} for i in range(4)]
    out = scheduler.forecast(tasks)
    affordable = [p for p in out["plans"] if p["affordable"]]
    blown = [p for p in out["plans"] if not p["affordable"]]
    assert len(affordable) == expected_affordable == 2
    assert blown
    assert all("projected_budget_exceeded" in p["violations"] for p in blown)
    assert out["tasks_affordable"] == expected_affordable
    # Projection only accumulates affordable tasks and never exceeds the limit.
    assert out["projected_energy"] <= out["window_limit"]
    assert out["projected_energy"] == round(expected_affordable * per_task_energy, 6)
    # Cumulative energy freezes once the budget is blown.
    assert blown[0]["cumulative_energy"] == out["projected_energy"]


def test_forecast_spent_window_shrinks_room(scheduler):
    # A single 0.45-unit task fits a fresh 1.0 window but not one with
    # 0.8 already spent — and this is flagged at PLAN level.
    scheduler.energy_budget.record(0.8)
    out = scheduler.forecast([{"id": "big", "category": "zzz", "compute_units": 45}])  # 0.45
    plan = out["plans"][0]
    assert plan["affordable"] is False
    assert "energy_budget_exceeded" in plan["violations"]
    assert out["window_spent_now"] == 0.8
    assert out["window_remaining_after"] == 0.2  # 1.0 - 0.8 spent - 0 projected


def test_forecast_spent_window_plus_projection(scheduler):
    # 0.3 already spent: the first 0.45 task fits (0.75), the second is
    # blown only by the cumulative projection (0.3 + 0.45 + 0.45 > 1.0).
    scheduler.energy_budget.record(0.3)
    tasks = [
        {"id": "p1", "category": "zzz", "compute_units": 45},
        {"id": "p2", "category": "zzz", "compute_units": 45},
    ]
    out = scheduler.forecast(tasks)
    first, second = out["plans"]
    assert first["affordable"] is True
    assert second["affordable"] is False
    assert "projected_budget_exceeded" in second["violations"]
    assert out["window_spent_now"] == 0.3
    assert out["window_remaining_after"] == round(1.0 - 0.3 - 0.45, 6)


def test_forecast_respects_policy_override(engine):
    engine.register_substrate(
        "cheap_slow",
        latency_base_ms=100.0,
        efficiency_gflops_per_watt=10.0,
        energy_cost_per_unit=0.001,
        capacity=100,
    )
    scheduler = EnergyAwareScheduler(engine)
    task = {"category": "zzz", "compute_units": 1}
    energy_first = scheduler.forecast([task])["plans"][0]
    latency_first = scheduler.forecast([task], policy="min_latency")["plans"][0]
    assert energy_first["selected_substrate"] == "cheap_slow"
    assert latency_first["selected_substrate"] == "photonic_optical"
    by_energy = scheduler.forecast([task])
    by_latency = scheduler.forecast([task], policy="min_latency")
    assert by_energy["policy"] == "min_energy"
    assert by_latency["policy"] == "min_latency"


def test_forecast_validates_input(scheduler):
    with pytest.raises(ValueError, match="list"):
        scheduler.forecast("nope")
    with pytest.raises(ValueError, match=r"tasks\[1\] must be a dict"):
        scheduler.forecast([{"id": 1}, "bad"])
    with pytest.raises(ValueError, match="unknown scheduling policy"):
        scheduler.forecast([], policy="esoteric")
    with pytest.raises(ValueError, match="1000-task forecast limit"):
        scheduler.forecast([{}] * (scheduler.FORECAST_MAX_TASKS + 1))


def test_forecast_no_route_is_flagged_unaffordable(scheduler):
    scheduler.latency_budget_ms = 0.01  # photonic (0.05ms) and everything slower is excluded
    out = scheduler.forecast([{"id": "blocked", "category": "zzz", "compute_units": 1}])
    plan = out["plans"][0]
    assert plan["selected_substrate"] is None
    assert plan["affordable"] is False
    assert "no_substrate_within_constraints" in plan["violations"]
    assert plan["expected_energy"] is None
    assert out["projected_energy"] == 0


def test_forecast_without_budget(engine):
    scheduler = EnergyAwareScheduler(engine)  # no rolling budget attached
    out = scheduler.forecast([{"id": "t", "category": "general", "compute_units": 3}])
    assert out["window_limit"] is None
    assert out["window_remaining_after"] is None
    assert out["window_spent_now"] == 0.0
    assert out["plans"][0]["affordable"] is True
    assert out["projected_energy"] == out["plans"][0]["expected_energy"]


def test_forecast_empty_batch(scheduler):
    out = scheduler.forecast([])
    assert out["tasks_total"] == 0
    assert out["tasks_affordable"] == 0
    assert out["projected_energy"] == 0
    assert out["plans"] == []


# ----------------------------------------------------------------------
# Dashboard endpoint
# ----------------------------------------------------------------------


@pytest.fixture()
def client():
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.8.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None


def test_forecast_endpoint_ok(client):
    resp = client.post(
        "/api/substrate/forecast",
        json={"tasks": [{"id": "x", "category": "general", "compute_units": 2}], "policy": "min_energy"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["policy"] == "min_energy"
    assert data["tasks_total"] == 1
    assert data["plans"][0]["task_id"] == "x"
    assert data["plans"][0]["affordable"] is True
    # A dry-run forecast executes nothing.
    assert client.get("/api/substrate/scheduler").json()["dispatches"] == 0
    assert client.get("/api/substrate/stats").json()["total_dispatches"] == 0


def test_forecast_endpoint_default_policy_and_window(client):
    resp = client.post("/api/substrate/forecast", json={"tasks": [{"compute_units": 10}]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["policy"] == "min_energy"  # scheduler default
    assert data["window_limit"] == 100.0  # dashboard singleton budget
    assert data["plans"][0]["task_id"] == "task"  # plan() fallback id


def test_forecast_endpoint_validation(client):
    no_tasks = client.post("/api/substrate/forecast", json={"policy": "min_energy"})
    assert no_tasks.status_code == 400
    assert "tasks" in no_tasks.json()["error"]
    assert client.post("/api/substrate/forecast", json={"tasks": "nope"}).status_code == 400
    assert client.post("/api/substrate/forecast", json={"tasks": [1]}).status_code == 400
    assert client.post("/api/substrate/forecast", json={"tasks": [], "policy": "bad"}).status_code == 400
    assert client.post("/api/substrate/forecast", json={"tasks": [], "policy": 5}).status_code == 400
    not_json = client.post("/api/substrate/forecast", content="not json", headers={"Content-Type": "application/json"})
    assert not_json.status_code == 400
    bad_body = client.post("/api/substrate/forecast", content="[1,2]", headers={"Content-Type": "application/json"})
    assert bad_body.status_code == 400
    over_cap = client.post("/api/substrate/forecast", json={"tasks": [{}] * 1001})
    assert over_cap.status_code == 400


def test_substrate_page_has_forecast_panel(client):
    html = client.get("/substrate").text
    assert "/api/substrate/forecast" in html
    assert "Dispatch Forecast" in html
    assert "forecast-tasks" in html
