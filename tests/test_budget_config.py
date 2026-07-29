"""Tests for runtime budget reconfiguration + persistence (v11.13.0)."""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.dashboard import create_dashboard
from aios_core.substrate_convergence import SubstrateConvergenceEngine
from aios_core.substrate_energy_scheduler import (
    BUDGET_FILE_FORMAT,
    EnergyAwareScheduler,
    RollingEnergyBudget,
    load_energy_budget,
)


@pytest.fixture()
def scheduler() -> EnergyAwareScheduler:
    engine = SubstrateConvergenceEngine()
    engine.register_substrate(
        "silicon",
        latency_base_ms=5.0,
        efficiency_gflops_per_watt=10.0,
        energy_cost_per_unit=0.1,
        capacity=100,
    )
    return EnergyAwareScheduler(
        engine,
        energy_budget=RollingEnergyBudget(limit=10.0, window_seconds=3600.0),
    )


def test_configure_replaces_limit_and_keeps_window(scheduler):
    report = scheduler.configure_budget(25.0)
    assert report["old"]["limit"] == 10.0
    assert report["old"]["window_seconds"] == 3600.0
    assert report["new"]["limit"] == 25.0
    assert report["new"]["window_seconds"] == 3600.0
    assert scheduler.energy_budget.limit == 25.0


def test_configure_carries_fresh_spends(scheduler):
    scheduler.energy_budget.record(3.0)
    scheduler.energy_budget.record(1.5)
    report = scheduler.configure_budget(50.0)
    # Both spends fall inside the (unchanged) window: carried over.
    assert report["carried_spends"] == 2
    assert report["carried_cost"] == pytest.approx(4.5)
    assert report["new"]["spent"] == pytest.approx(4.5)
    assert scheduler.energy_budget.spent() == pytest.approx(4.5)


def test_configure_shorter_window_drops_old_spends(scheduler):
    scheduler.energy_budget.record(2.0)
    # Inject a spend from 2 hours ago (outside any shorter window).
    scheduler.energy_budget._spends.append((time.time() - 7200, 9.0))
    report = scheduler.configure_budget(20.0, window_seconds=600.0)
    assert report["new"]["window_seconds"] == 600.0
    assert report["carried_spends"] == 1
    assert report["carried_cost"] == pytest.approx(2.0)
    assert scheduler.energy_budget.spent() == pytest.approx(2.0)


def test_configure_without_existing_budget():
    engine = SubstrateConvergenceEngine()
    engine.register_substrate("silicon", 5.0, 10.0, 0.1, 100)
    scheduler = EnergyAwareScheduler(engine)  # no budget configured
    report = scheduler.configure_budget(5.0)
    assert report["old"] is None
    assert report["new"]["limit"] == 5.0
    assert report["new"]["window_seconds"] == 3600.0
    assert report["carried_spends"] == 0


def test_configure_validation(scheduler):
    with pytest.raises(ValueError, match="budget limit must be positive"):
        scheduler.configure_budget(0)
    with pytest.raises(ValueError, match="budget limit must be positive"):
        scheduler.configure_budget(-5)
    with pytest.raises(ValueError, match="budget limit must be a number"):
        scheduler.configure_budget("lots")
    with pytest.raises(ValueError, match="window_seconds must be positive"):
        scheduler.configure_budget(5.0, window_seconds=0)
    with pytest.raises(ValueError, match="window_seconds must be a number"):
        scheduler.configure_budget(5.0, window_seconds="hour")
    # Failed attempts leave the budget untouched.
    assert scheduler.energy_budget.limit == 10.0


def test_save_and_load_roundtrip(scheduler, tmp_path):
    target = tmp_path / "nested" / "energy_budget.json"
    payload = scheduler.save_budget(target)
    assert payload["format"] == BUDGET_FILE_FORMAT
    assert payload["limit"] == 10.0
    assert payload["window_seconds"] == 3600.0
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["format"] == BUDGET_FILE_FORMAT
    loaded = load_energy_budget(target)
    assert loaded is not None
    assert loaded.limit == 10.0
    assert loaded.window_seconds == 3600.0
    assert loaded.spent() == 0.0  # config only — no live spends persisted


def test_load_missing_malformed_and_invalid(tmp_path):
    assert load_energy_budget(tmp_path / "absent.json") is None
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        load_energy_budget(bad_json)
    wrong_format = tmp_path / "wrong.json"
    wrong_format.write_text(json.dumps({"format": 99, "limit": 1, "window_seconds": 2}), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported format"):
        load_energy_budget(wrong_format)
    non_numeric = tmp_path / "nan.json"
    non_numeric.write_text(
        json.dumps({"format": BUDGET_FILE_FORMAT, "limit": None, "window_seconds": 3600}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="non-numeric"):
        load_energy_budget(non_numeric)
    negative = tmp_path / "neg.json"
    negative.write_text(
        json.dumps({"format": BUDGET_FILE_FORMAT, "limit": -1.0, "window_seconds": 3600}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="budget limit must be positive"):
        load_energy_budget(negative)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_module, "_BUDGET_PATH", tmp_path / "energy_budget.json")
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.13.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None


def test_endpoint_budget_applies_and_persists(client, tmp_path):
    resp = client.post("/api/substrate/budget", json={"limit": 42.5, "window_seconds": 600})
    assert resp.status_code == 200
    data = resp.json()
    assert data["new"]["limit"] == 42.5
    assert data["new"]["window_seconds"] == 600.0
    assert data["budget_file"] == str(tmp_path / "energy_budget.json")
    # Live scheduler report reflects the new budget.
    report = client.get("/api/substrate/scheduler").json()
    assert report["energy_budget"]["limit"] == 42.5
    # Config was persisted and a fresh scheduler would load it.
    saved = load_energy_budget(tmp_path / "energy_budget.json")
    assert saved.limit == 42.5
    assert saved.window_seconds == 600.0


def test_endpoint_budget_reloads_into_fresh_scheduler(client, tmp_path):
    client.post("/api/substrate/budget", json={"limit": 7.5})
    dashboard_module._energy_scheduler = None  # simulate dashboard restart
    report = client.get("/api/substrate/scheduler").json()
    assert report["energy_budget"]["limit"] == 7.5
    assert report["energy_budget"]["window_seconds"] == 3600.0


def test_endpoint_budget_validation(client):
    assert client.post("/api/substrate/budget", json={}).status_code == 400
    resp = client.post("/api/substrate/budget", json={"limit": -1})
    assert resp.status_code == 400
    assert "limit" in resp.json()["error"]
    resp = client.post("/api/substrate/budget", json={"limit": 5, "window_seconds": 0})
    assert resp.status_code == 400
    assert "window_seconds" in resp.json()["error"]
    resp = client.post("/api/substrate/budget", content="not-json", headers={"Content-Type": "application/json"})
    assert resp.status_code == 400
    # Default budget still in place.
    assert client.get("/api/substrate/scheduler").json()["energy_budget"]["limit"] == 100.0
