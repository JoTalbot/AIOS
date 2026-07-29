"""Tests for SLO alerting on the aggregate health score (v11.10.0)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.agent_memory_system import AgentMemorySystem, MemoryType
from aios_core.dashboard import create_dashboard
from aios_core.slo_alerts import evaluate_health_alerts
from aios_core.substrate_convergence import SubstrateConvergenceEngine
from aios_core.substrate_energy_scheduler import EnergyAwareScheduler


def _strong_memory() -> AgentMemorySystem:
    memory = AgentMemorySystem()
    memory.record("olx", "login", "success", memory_type=MemoryType.LONG_TERM)
    return memory


def test_healthy_system_has_no_alerts():
    out = evaluate_health_alerts(
        memory_system=_strong_memory(),
        engine=SubstrateConvergenceEngine(),
        scheduler=EnergyAwareScheduler(SubstrateConvergenceEngine()),
    )
    assert out["ok"] is True
    assert out["alert_count"] == 0
    assert out["alerts"] == []
    assert out["worst_severity"] is None
    assert out["score"] == 100.0
    assert out["status"] == "healthy"
    assert out["thresholds"] == {"warning": 80.0, "critical": 50.0}


def test_critical_fleet_fires_aggregate_and_component():
    engine = SubstrateConvergenceEngine()
    for sub in engine.substrates.values():
        sub["health"] = 0.3
    out = evaluate_health_alerts(engine=engine)
    assert out["ok"] is False
    assert out["worst_severity"] == "critical"
    subjects = {a["subject"]: a["severity"] for a in out["alerts"]}
    assert subjects == {"aggregate": "critical", "substrate_fleet": "critical"}
    assert all("below the critical threshold" in a["message"] for a in out["alerts"])
    assert out["alert_count"] == 2


def test_mixed_severities_report_worst():
    # Fleet drags its component to critical while the aggregate survives
    # in the warning band thanks to strong memory (score 60).
    engine = SubstrateConvergenceEngine()
    for sub in engine.substrates.values():
        sub["health"] = 0.3
    out = evaluate_health_alerts(memory_system=_strong_memory(), engine=engine)
    subjects = {a["subject"]: a["severity"] for a in out["alerts"]}
    assert subjects["aggregate"] == "warning"
    assert subjects["substrate_fleet"] == "critical"
    assert out["worst_severity"] == "critical"
    assert out["status"] == "degraded"


def test_scheduler_only_failure_is_critical():
    engine = SubstrateConvergenceEngine()
    scheduler = EnergyAwareScheduler(engine, latency_budget_ms=0.001)  # forces fallback
    scheduler.dispatch({"id": "s1", "compute_units": 1})
    out = evaluate_health_alerts(scheduler=scheduler)
    assert out["score"] == 0.0
    assert out["status"] == "critical"
    subjects = {a["subject"] for a in out["alerts"]}
    assert subjects == {"aggregate", "scheduler_efficiency"}


def test_custom_thresholds_respected():
    engine = SubstrateConvergenceEngine()
    for sub in engine.substrates.values():
        sub["health"] = 0.9  # fleet score 90
    relaxed = evaluate_health_alerts(engine=engine, warning=85.0, critical=10.0)
    assert relaxed["ok"] is True
    strict = evaluate_health_alerts(engine=engine, warning=95.0, critical=10.0)
    assert strict["ok"] is False
    assert {a["severity"] for a in strict["alerts"]} == {"warning"}


def test_threshold_validation():
    with pytest.raises(ValueError, match="critical < warning"):
        evaluate_health_alerts(warning=50.0, critical=80.0)
    with pytest.raises(ValueError):
        evaluate_health_alerts(warning=100.0, critical=100.0)
    with pytest.raises(ValueError):
        evaluate_health_alerts(warning=101.0)
    with pytest.raises(ValueError):
        evaluate_health_alerts(critical=-1.0)


def test_no_data_is_ok():
    out = evaluate_health_alerts()
    assert out["ok"] is True
    assert out["score"] is None
    assert out["status"] == "no_data"


# ----------------------------------------------------------------------
# Dashboard endpoint + panel wiring
# ----------------------------------------------------------------------


@pytest.fixture()
def client():
    dashboard_module._memory_system = None
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.10.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._memory_system = None
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None


def test_alerts_endpoint_ok_on_seeded(client):
    resp = client.get("/api/health/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["alert_count"] == 0
    assert data["status"] == "healthy"


def test_alerts_endpoint_reflects_damage(client):
    engine = dashboard_module._get_substrate_engine()
    for sub in engine.substrates.values():
        sub["health"] = 0.2
    data = client.get("/api/health/alerts").json()
    assert data["ok"] is False
    assert data["worst_severity"] == "critical"
    subjects = {a["subject"] for a in data["alerts"]}
    assert "substrate_fleet" in subjects


def test_alerts_endpoint_validation(client):
    assert client.get("/api/health/alerts?warn=abc").status_code == 400
    assert client.get("/api/health/alerts?critical=xyz").status_code == 400
    assert client.get("/api/health/alerts?warn=40&critical=50").status_code == 400
    ok = client.get("/api/health/alerts?warn=95&critical=70")
    assert ok.status_code == 200
    assert ok.json()["thresholds"] == {"warning": 95.0, "critical": 70.0}
    # Seeded score 100 stays below the 95 warning? No: 100 >= 95 -> ok.
    assert ok.json()["ok"] is True


def test_substrate_page_wires_alerts(client):
    resp = client.get("/substrate")
    assert "/api/health/alerts" in resp.text
    assert "health-detail" in resp.text
