"""Tests for history replay / routing-drift analysis + endpoint (v11.11.0)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.dashboard import create_dashboard
from aios_core.substrate_convergence import SubstrateConvergenceEngine
from aios_core.substrate_energy_scheduler import EnergyAwareScheduler


@pytest.fixture()
def engine() -> SubstrateConvergenceEngine:
    eng = SubstrateConvergenceEngine()
    eng.execute_substrate_task({"id": "r1", "category": "general", "compute_units": 2})
    return eng


def _record_of(engine: SubstrateConvergenceEngine) -> dict:
    """A dispatch_history entry shaped like a CSV-export row (dict of values)."""
    return dict(engine.dispatch_history[-1])


def test_replay_matches_current_routing(engine):
    scheduler = EnergyAwareScheduler(engine)
    report = scheduler.replay([_record_of(engine)])
    assert report["records"] == 1
    row = report["rows"][0]
    assert row["task_id"] == "r1"
    assert row["recorded_substrate"] == "silicon_x86_arm"
    assert row["recorded_energy"] == 0.2  # 2 units * 0.10
    # Units reconstructed exactly: plan for category general still picks silicon.
    assert row["planned_substrate"] == "silicon_x86_arm"
    assert row["planned_energy"] == 0.2
    assert row["matching"] is True
    assert row["energy_delta"] == 0.0
    assert report["matching"] == 1
    assert report["match_pct"] == 100.0
    assert report["potential_savings"] == 0.0
    assert report["unknown_substrates"] == []
    # Replay does not execute anything.
    assert scheduler.report()["dispatches"] == 0
    assert engine.stats()["total_dispatches"] == 1


def test_replay_detects_drift_with_cheaper_substrate(engine):
    engine.register_substrate(
        "cheap_general",
        latency_base_ms=5.0,
        efficiency_gflops_per_watt=10.0,
        energy_cost_per_unit=0.001,
        capacity=100,
        task_affinity=["general"],
    )
    scheduler = EnergyAwareScheduler(engine)
    report = scheduler.replay([_record_of(engine)])
    row = report["rows"][0]
    assert row["planned_substrate"] == "cheap_general"
    assert row["matching"] is False
    assert row["planned_energy"] == 0.002  # 2 units * 0.001
    assert row["energy_delta"] == 0.198
    assert report["potential_savings"] == 0.198  # 0.2 - 0.002
    assert report["match_pct"] == 0.0


def test_replay_flags_unknown_substrates(engine):
    scheduler = EnergyAwareScheduler(engine)
    report = scheduler.replay([{"task_id": "ghost", "selected_substrate": "quantum_legacy", "energy_cost": 1.0}])
    assert report["unknown_substrates"] == ["quantum_legacy"]
    row = report["rows"][0]
    assert row["matching"] is False
    assert row["planned_energy"] is not None  # still planned (units fall back to 1)


def test_replay_respects_policy_override(engine):
    engine.register_substrate(
        "cheap_slow",
        latency_base_ms=100.0,
        efficiency_gflops_per_watt=10.0,
        energy_cost_per_unit=0.001,
        capacity=100,
    )
    scheduler = EnergyAwareScheduler(engine)
    record = dict(_record_of(engine))
    record["category"] = "zzz"  # no affinity -> all substrates are candidates
    record["selected_substrate"] = "cheap_slow"
    record["energy_cost"] = 0.1  # 100 units at 0.001
    by_energy = scheduler.replay([record])["rows"][0]
    by_latency = scheduler.replay([record], policy="min_latency")["rows"][0]
    assert by_energy["planned_substrate"] == "cheap_slow"
    assert by_energy["matching"] is True
    assert by_latency["planned_substrate"] == "photonic_optical"
    assert by_latency["matching"] is False
    assert by_latency["energy_delta"] == -0.9  # recorded 0.1 vs planned 100 units * 0.01


def test_replay_honors_explicit_compute_units(engine):
    scheduler = EnergyAwareScheduler(engine)
    record = _record_of(engine)
    record["compute_units"] = 5  # overrides reconstruction (would be 2)
    row = scheduler.replay([record])["rows"][0]
    assert row["planned_energy"] == 0.5  # 5 * 0.10 on silicon


def test_replay_validation(engine):
    scheduler = EnergyAwareScheduler(engine)
    with pytest.raises(ValueError, match="list"):
        scheduler.replay("nope")
    with pytest.raises(ValueError, match=r"records\[0\] must be a dict"):
        scheduler.replay(["x"])
    with pytest.raises(ValueError, match="energy_cost must be a number"):
        scheduler.replay([{"task_id": "b", "selected_substrate": "silicon_x86_arm", "energy_cost": "abc"}])
    with pytest.raises(ValueError, match="unknown scheduling policy"):
        scheduler.replay([], policy="nope")
    with pytest.raises(ValueError, match="1000-record replay limit"):
        scheduler.replay([{}] * (scheduler.FORECAST_MAX_TASKS + 1))


# ----------------------------------------------------------------------
# Dashboard endpoint + panel wiring
# ----------------------------------------------------------------------


@pytest.fixture()
def client():
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.11.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None


def test_replay_endpoint_csv_roundtrip(client):
    client.post(
        "/api/substrate/schedule", json={"id": "csv-r1", "category": "general", "compute_units": 2, "execute": True}
    )
    csv_text = client.get("/api/substrate/history/export").text
    resp = client.post("/api/substrate/replay", content=csv_text, headers={"Content-Type": "text/csv"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["records"] == 1
    assert data["matching"] == 1
    assert data["rows"][0]["task_id"] == "csv-r1"
    assert data["rows"][0]["planned_substrate"] == "silicon_x86_arm"
    # Nothing was executed by the replay itself.
    assert client.get("/api/substrate/scheduler").json()["dispatches"] == 1

    with_policy = client.post(
        "/api/substrate/replay?policy=balanced", content=csv_text, headers={"Content-Type": "text/csv"}
    )
    assert with_policy.status_code == 200
    assert with_policy.json()["policy"] == "balanced"


def test_replay_endpoint_json_path(client):
    resp = client.post(
        "/api/substrate/replay",
        json={"records": [{"task_id": "j1", "selected_substrate": "silicon_x86_arm", "energy_cost": 0.2}]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["records"] == 1
    assert data["policy"] == "min_energy"
    assert data["rows"][0]["matching"] is True


def test_replay_endpoint_validation(client):
    assert (
        client.post("/api/substrate/replay", content="col1,col2\n1,2", headers={"Content-Type": "text/csv"}).status_code
        == 400
    )
    assert client.post("/api/substrate/replay", content="not data at all").status_code == 400
    assert client.post("/api/substrate/replay", json={"records": "nope"}).status_code == 400
    assert client.post("/api/substrate/replay", json={"records": [], "policy": 7}).status_code == 400
    assert client.post("/api/substrate/replay", json={"records": [], "policy": "nope"}).status_code == 400
    ok = client.post("/api/substrate/replay?policy=min_latency", json={"records": []})
    assert ok.status_code == 200  # JSON mode ignores the query policy (documented)
    assert ok.json()["policy"] == "min_energy"


def test_substrate_page_has_replay_picker(client):
    resp = client.get("/substrate")
    assert 'id="replay-file"' in resp.text
    assert "/api/substrate/replay" in resp.text
    assert "runReplay" in resp.text
