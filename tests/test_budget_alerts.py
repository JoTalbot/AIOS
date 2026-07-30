"""Tests for rolling-budget pressure alerts + metric series (v11.14.0)."""

from __future__ import annotations

import re
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.dashboard import create_dashboard
from aios_core.slo_alerts import evaluate_budget_alerts
from aios_core.substrate_convergence import SubstrateConvergenceEngine
from aios_core.substrate_energy_scheduler import EnergyAwareScheduler, RollingEnergyBudget


@pytest.fixture()
def scheduler() -> EnergyAwareScheduler:
    engine = SubstrateConvergenceEngine()
    engine.register_substrate("silicon", 5.0, 10.0, 0.1, 100)
    return EnergyAwareScheduler(
        engine,
        energy_budget=RollingEnergyBudget(limit=10.0, window_seconds=3600.0),
    )


def test_pressure_ratio_and_to_dict(scheduler):
    budget = scheduler.energy_budget
    assert budget.pressure() == 0.0
    assert budget.to_dict()["pressure"] == 0.0
    budget.record(2.5)
    assert budget.pressure() == pytest.approx(0.25)
    assert budget.to_dict()["pressure"] == pytest.approx(0.25)


def test_pressure_exceeds_one_after_shrinking_reconfigure(scheduler):
    scheduler.energy_budget.record(8.0)
    scheduler.configure_budget(4.0)  # spend carried, limit cut below it
    assert scheduler.energy_budget.pressure() == pytest.approx(2.0)
    report = evaluate_budget_alerts(scheduler=scheduler)
    assert report["status"] == "critical"
    assert report["pressure"] == pytest.approx(2.0)


def test_evaluate_no_scheduler_or_no_budget():
    report = evaluate_budget_alerts(scheduler=None)
    assert report["available"] is False
    assert report["status"] == "no_budget"
    assert report["ok"] is True
    assert report["alerts"] == []
    engine = SubstrateConvergenceEngine()
    engine.register_substrate("silicon", 5.0, 10.0, 0.1, 100)
    bare = EnergyAwareScheduler(engine)  # no budget configured
    assert evaluate_budget_alerts(scheduler=bare)["status"] == "no_budget"


def test_evaluate_ok_warning_critical_bands(scheduler):
    scheduler.energy_budget.record(5.0)  # pressure 0.5
    report = evaluate_budget_alerts(scheduler=scheduler)
    assert report["status"] == "ok"
    assert report["ok"] is True
    assert report["alert_count"] == 0
    assert report["worst_severity"] is None

    scheduler.energy_budget.record(3.0)  # pressure 0.8
    report = evaluate_budget_alerts(scheduler=scheduler)
    assert report["status"] == "warning"
    assert report["ok"] is False
    assert report["alert_count"] == 1
    alert = report["alerts"][0]
    assert alert["subject"] == "energy_budget"
    assert alert["severity"] == "warning"
    assert alert["spent"] == pytest.approx(8.0)
    assert alert["limit"] == 10.0
    assert "0.8" in alert["message"]

    scheduler.energy_budget.record(2.5)  # pressure 1.05
    report = evaluate_budget_alerts(scheduler=scheduler)
    assert report["status"] == "critical"
    assert report["worst_severity"] == "critical"


def test_evaluate_custom_ratios(scheduler):
    scheduler.energy_budget.record(4.0)  # pressure 0.4
    report = evaluate_budget_alerts(scheduler=scheduler, warning_ratio=0.3, critical_ratio=0.5)
    assert report["status"] == "warning"
    assert report["thresholds"] == {"warning_ratio": 0.3, "critical_ratio": 0.5}
    # Same pressure, higher thresholds: back to ok.
    assert evaluate_budget_alerts(scheduler=scheduler, warning_ratio=0.5, critical_ratio=0.9)["status"] == "ok"
    # Boundary: pressure exactly AT the warning ratio fires (>= semantics).
    assert evaluate_budget_alerts(scheduler=scheduler, warning_ratio=0.4, critical_ratio=0.9)["status"] == "warning"


def test_evaluate_ratio_validation(scheduler):
    with pytest.raises(ValueError, match="0 <= warning_ratio < critical_ratio"):
        evaluate_budget_alerts(scheduler=scheduler, warning_ratio=1.0, critical_ratio=0.5)
    with pytest.raises(ValueError, match="0 <= warning_ratio < critical_ratio"):
        evaluate_budget_alerts(scheduler=scheduler, warning_ratio=-0.1)
    with pytest.raises(ValueError, match="must be numbers"):
        evaluate_budget_alerts(scheduler=scheduler, warning_ratio="high")


@pytest.fixture()
def client():
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.14.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None


def test_budget_alerts_endpoint_ok_and_validation(client):
    resp = client.get("/api/substrate/budget/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is True
    assert data["status"] == "ok"
    assert data["pressure"] == 0.0
    assert data["budget"]["limit"] == 100.0
    assert data["thresholds"] == {"warning_ratio": 0.8, "critical_ratio": 1.0}
    assert client.get("/api/substrate/budget/alerts?warning=0.9&critical=0.5").status_code == 400
    assert client.get("/api/substrate/budget/alerts?warning=oops").status_code == 400


def test_budget_alerts_endpoint_fires_after_spend(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_module, "_BUDGET_PATH", tmp_path / "energy_budget.json")
    # Shrink the budget, then spend most of it via real dispatches.
    client.post("/api/substrate/budget", json={"limit": 2.0})
    for i in range(18):  # 18 x ~0.1 = ~1.8 units → pressure ~0.9
        client.post(
            "/api/substrate/schedule",
            json={"id": f"burn-{i}", "category": "general", "compute_units": 1, "execute": True},
        )
    data = client.get("/api/substrate/budget/alerts").json()
    assert data["status"] in ("warning", "critical")
    assert data["alert_count"] == 1
    assert data["alerts"][0]["severity"] == data["status"]


def test_metrics_endpoint_exports_pressure_series(client):
    body = client.get("/api/metrics").text
    assert re.search(r"^aios_energy_budget_pressure [0-9.]+$", body, re.M)
    # Seeded scheduler has spent nothing yet in this fixture.
    assert "aios_energy_budget_pressure 0" in body


def test_substrate_page_has_pressure_row_and_alerts_fetch(client):
    resp = client.get("/substrate")
    assert resp.status_code == 200
    assert 'id="budget-pressure-view"' in resp.text
    assert "/api/substrate/budget/alerts" in resp.text
