"""Tests for the health/SLO series in the Prometheus export (v11.11.0)."""

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


def test_render_includes_slo_block_when_report_given():
    engine = SubstrateConvergenceEngine()
    scheduler = EnergyAwareScheduler(engine, energy_budget=RollingEnergyBudget(limit=10.0))
    report = evaluate_health_alerts(engine=engine, scheduler=scheduler)
    text = render_prometheus(engine=engine, scheduler=scheduler, alerts_report=report)
    assert "aios_health_score 100" in text
    assert "aios_health_evaluated_components 1" in text  # scheduler has no dispatches yet
    assert "aios_slo_ok 1" in text
    assert 'aios_slo_alerts{severity="warning"} 0' in text
    assert 'aios_slo_alerts{severity="critical"} 0' in text


def test_render_slo_counts_alerts_by_severity():
    engine = SubstrateConvergenceEngine()
    for sub in engine.substrates.values():
        sub["health"] = 0.3
    report = evaluate_health_alerts(engine=engine)
    text = render_prometheus(alerts_report=report)
    assert "aios_health_score 30" in text
    assert "aios_slo_ok 0" in text
    # aggregate critical + substrate_fleet critical
    assert 'aios_slo_alerts{severity="critical"} 2' in text
    assert 'aios_slo_alerts{severity="warning"} 0' in text


def test_render_omits_score_and_slo_without_report():
    text = render_prometheus()
    assert "aios_health_score" not in text
    assert "aios_slo_alerts" not in text
    assert "aios_slo_ok" not in text


def test_render_slo_omits_score_for_no_data():
    text = render_prometheus(
        alerts_report={"score": None, "status": "no_data", "ok": True, "alerts": [], "evaluated": 0}
    )
    assert "aios_health_score" not in text  # no numeric score to export
    assert "aios_slo_ok 1" in text
    assert "aios_health_evaluated_components 0" in text


# ----------------------------------------------------------------------
# Endpoint wiring
# ----------------------------------------------------------------------


@pytest.fixture()
def client():
    dashboard_module._memory_system = None
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.11.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._memory_system = None
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None


def test_metrics_endpoint_exports_health_and_slo(client):
    body = client.get("/api/metrics").text
    assert "aios_health_score 100" in body  # seeded singletons are healthy
    assert "aios_slo_ok 1" in body
    assert 'aios_slo_alerts{severity="critical"} 0' in body


def test_metrics_endpoint_exports_alerts_after_damage(client):
    engine = dashboard_module._get_substrate_engine()
    for sub in engine.substrates.values():
        sub["health"] = 0.2
    body = client.get("/api/metrics").text
    assert "aios_slo_ok 0" in body
    # Fleet component is critical; seeded memory drags the aggregate into
    # the warning band -> 1 critical + 1 warning.
    assert 'aios_slo_alerts{severity="critical"} 1' in body
    assert 'aios_slo_alerts{severity="warning"} 1' in body
