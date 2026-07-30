"""Tests for budget pressure rolling up into unified health alerts (v11.15.0)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.dashboard import create_dashboard
from aios_core.metrics_export import render_prometheus
from aios_core.slo_alerts import evaluate_health_alerts
from aios_core.substrate_convergence import SubstrateConvergenceEngine
from aios_core.substrate_energy_scheduler import EnergyAwareScheduler, RollingEnergyBudget


def _engine() -> SubstrateConvergenceEngine:
    engine = SubstrateConvergenceEngine()
    engine.register_substrate("silicon", 5.0, 10.0, 0.1, 100)
    return engine


def test_no_budget_keeps_previous_behaviour():
    report = evaluate_health_alerts(scheduler=EnergyAwareScheduler(_engine()))
    assert report["ok"] is True
    assert "budget" in report
    assert report["budget"]["status"] == "no_budget"
    assert report["budget"]["available"] is False
    for alert in report["alerts"]:
        assert alert["subject"] != "energy_budget"


def test_calm_budget_adds_no_alert():
    scheduler = EnergyAwareScheduler(_engine(), energy_budget=RollingEnergyBudget(limit=100.0, window_seconds=3600.0))
    scheduler.energy_budget.record(10.0)  # pressure 0.1
    report = evaluate_health_alerts(scheduler=scheduler)
    assert report["ok"] is True
    assert report["alert_count"] == 0
    assert report["budget"]["status"] == "ok"
    assert report["budget"]["pressure"] == pytest.approx(0.1)


def test_warning_pressure_enters_unified_report():
    scheduler = EnergyAwareScheduler(_engine(), energy_budget=RollingEnergyBudget(limit=10.0, window_seconds=3600.0))
    scheduler.energy_budget.record(9.0)  # pressure 0.9
    report = evaluate_health_alerts(scheduler=scheduler)
    assert report["ok"] is False
    assert report["alert_count"] == 1
    assert report["worst_severity"] == "warning"
    (alert,) = report["alerts"]
    assert alert["subject"] == "energy_budget"
    assert alert["severity"] == "warning"
    assert report["budget"]["status"] == "warning"


def test_critical_pressure_dominates_worst_severity():
    engine = _engine()
    for sub in engine.substrates.values():
        sub["health"] = 0.7  # fleet warning (score 70 < 80)
    scheduler = EnergyAwareScheduler(engine, energy_budget=RollingEnergyBudget(limit=10.0, window_seconds=3600.0))
    scheduler.energy_budget.record(11.0)  # pressure 1.1 > critical ratio
    report = evaluate_health_alerts(engine=engine, scheduler=scheduler)
    subjects = {a["subject"] for a in report["alerts"]}
    assert "energy_budget" in subjects
    assert "substrate_fleet" in subjects
    # Budget critical outranks the fleet warning.
    assert report["worst_severity"] == "critical"
    assert report["ok"] is False


def test_custom_budget_ratios_in_rollup():
    scheduler = EnergyAwareScheduler(_engine(), energy_budget=RollingEnergyBudget(limit=10.0, window_seconds=3600.0))
    scheduler.energy_budget.record(4.0)  # pressure 0.4
    assert evaluate_health_alerts(scheduler=scheduler)["ok"] is True
    strict = evaluate_health_alerts(scheduler=scheduler, budget_warning_ratio=0.3, budget_critical_ratio=0.5)
    assert strict["ok"] is False
    assert strict["alerts"][0]["subject"] == "energy_budget"
    with pytest.raises(ValueError):
        evaluate_health_alerts(scheduler=scheduler, budget_warning_ratio=0.9, budget_critical_ratio=0.5)


def test_slo_metrics_count_budget_alerts():
    scheduler = EnergyAwareScheduler(_engine(), energy_budget=RollingEnergyBudget(limit=10.0, window_seconds=3600.0))
    scheduler.energy_budget.record(9.0)  # budget warning
    report = evaluate_health_alerts(scheduler=scheduler)
    text = render_prometheus(scheduler=scheduler, alerts_report=report)
    assert "aios_slo_ok 0" in text
    assert 'aios_slo_alerts{severity="warning"} 1' in text
    assert 'aios_slo_alerts{severity="critical"} 0' in text


@pytest.fixture()
def client():
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.15.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None


def test_health_alerts_endpoint_carries_budget_subreport(client):
    data = client.get("/api/health/alerts").json()
    assert "budget" in data
    assert data["budget"]["available"] is True
    assert data["budget"]["status"] == "ok"
    assert data["ok"] is True


def test_health_alerts_endpoint_reflects_pressure(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_module, "_BUDGET_PATH", tmp_path / "budget.json")
    client.post("/api/substrate/budget", json={"limit": 2.0})
    for i in range(18):  # ~1.8 units → pressure ~0.9
        client.post(
            "/api/substrate/schedule",
            json={"id": f"rb-{i}", "category": "general", "compute_units": 1, "execute": True},
        )
    data = client.get("/api/health/alerts").json()
    assert data["ok"] is False
    assert "energy_budget" in {a["subject"] for a in data["alerts"]}
    assert data["budget"]["status"] in ("warning", "critical")
    # And the Prometheus scrape counts it automatically.
    body = client.get("/api/metrics").text
    assert "aios_slo_ok 0" in body
