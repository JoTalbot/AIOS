"""Tests for the aggregate system health score + endpoint + panel (v11.9.0)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.agent_memory_system import AgentMemorySystem, MemoryType
from aios_core.dashboard import create_dashboard
from aios_core.health_score import compute_health_score
from aios_core.substrate_convergence import SubstrateConvergenceEngine
from aios_core.substrate_energy_scheduler import EnergyAwareScheduler, RollingEnergyBudget


def _strong_memory() -> AgentMemorySystem:
    memory = AgentMemorySystem()
    memory.record("olx", "login", "success", memory_type=MemoryType.LONG_TERM)
    memory.record("olx", "collect", "success", memory_type=MemoryType.LONG_TERM)
    return memory


def test_fresh_system_is_healthy_without_scheduler_signal():
    out = compute_health_score(
        memory_system=_strong_memory(),
        engine=SubstrateConvergenceEngine(),
        scheduler=EnergyAwareScheduler(SubstrateConvergenceEngine()),
    )
    assert out["status"] == "healthy"
    assert out["score"] == 100.0  # substrates 100 + memory 100, scheduler n/a
    assert out["evaluated"] == 2
    assert out["components"]["scheduler_efficiency"]["available"] is False
    assert out["components"]["scheduler_efficiency"]["score"] is None
    assert out["components"]["substrate_fleet"]["score"] == 100.0
    assert out["components"]["memory_vitality"]["score"] == 100.0


def test_scheduler_efficiency_counts_once_dispatches_exist():
    engine = SubstrateConvergenceEngine()
    scheduler = EnergyAwareScheduler(engine, energy_budget=RollingEnergyBudget(limit=10.0))
    scheduler.dispatch({"id": "h1", "category": "general", "compute_units": 2})
    out = compute_health_score(engine=engine, scheduler=scheduler)
    comp = out["components"]["scheduler_efficiency"]
    assert comp["available"] is True
    # min_energy == baseline here: 0% savings, 0% fallbacks -> 0.6*0 + 0.4*100 = 40
    assert comp["score"] == 40.0
    assert comp["detail"]["fallback_rate"] == 0.0
    # (0.4*100 + 0.3*40) / 0.7 = 74.29 -> degraded band
    assert out["score"] == 74.29
    assert out["status"] == "degraded"


def test_fallback_dispatches_drag_efficiency_to_zero():
    engine = SubstrateConvergenceEngine()
    scheduler = EnergyAwareScheduler(engine, latency_budget_ms=0.001)  # forces fallback
    scheduler.dispatch({"id": "f1", "compute_units": 1})
    out = compute_health_score(scheduler=scheduler)
    comp = out["components"]["scheduler_efficiency"]
    assert comp["detail"]["fallback_rate"] == 1.0
    assert comp["score"] == 0.0
    assert out["score"] == 0.0
    assert out["status"] == "critical"


def test_memory_component_unavailable_when_empty():
    out = compute_health_score(
        memory_system=AgentMemorySystem(),
        engine=SubstrateConvergenceEngine(),
    )
    assert out["components"]["memory_vitality"]["available"] is False
    assert out["score"] == 100.0  # substrate fleet only
    assert out["status"] == "healthy"


def test_degraded_fleet_lowers_score():
    engine = SubstrateConvergenceEngine()
    for sub in engine.substrates.values():
        sub["health"] = 0.3
    out = compute_health_score(memory_system=_strong_memory(), engine=engine)
    # (0.4*30 + 0.3*100) / 0.7 = 60 -> degraded
    assert out["components"]["substrate_fleet"]["score"] == 30.0
    assert out["score"] == 60.0
    assert out["status"] == "degraded"

    for sub in engine.substrates.values():
        sub["health"] = 0.1
    out = compute_health_score(engine=engine)
    assert out["score"] == 10.0
    assert out["status"] == "critical"


def test_inactive_substrates_excluded_from_fleet():
    engine = SubstrateConvergenceEngine()
    engine.substrates["quantum_qpu"]["active"] = False
    engine.substrates["quantum_qpu"]["health"] = 0.0
    out = compute_health_score(engine=engine)
    assert out["components"]["substrate_fleet"]["detail"]["active_substrates"] == 4
    assert out["score"] == 100.0


def test_no_sources_reports_no_data():
    out = compute_health_score()
    assert out == {"score": None, "status": "no_data", "components": {}, "evaluated": 0}


# ----------------------------------------------------------------------
# Dashboard endpoint + panel
# ----------------------------------------------------------------------


@pytest.fixture()
def client():
    dashboard_module._memory_system = None
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.9.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._memory_system = None
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None


def test_health_endpoint_shape(client):
    resp = client.get("/api/health/score")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data) == {"score", "status", "components", "evaluated"}
    assert data["status"] == "healthy"
    assert data["score"] == 100.0  # seeded singletons: perfect fleet + memory
    assert set(data["components"]) == {"substrate_fleet", "scheduler_efficiency", "memory_vitality"}
    assert data["components"]["scheduler_efficiency"]["available"] is False


def test_health_endpoint_reflects_damage(client):
    engine = dashboard_module._get_substrate_engine()
    for sub in engine.substrates.values():
        sub["health"] = 0.1
    data = client.get("/api/health/score").json()
    assert data["status"] == "critical"
    assert data["components"]["substrate_fleet"]["score"] == 10.0


def test_substrate_page_has_health_panel(client):
    resp = client.get("/substrate")
    assert "System Health Score" in resp.text
    assert "/api/health/score" in resp.text
    assert "health-score" in resp.text
    assert "health-status" in resp.text
