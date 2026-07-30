"""Tests for scheduler-dispatch retention preview + guarded purge (v11.14.0)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.dashboard import create_dashboard
from aios_core.retention import plan_retention_purge
from aios_core.substrate_convergence import SubstrateConvergenceEngine
from aios_core.substrate_energy_scheduler import EnergyAwareScheduler, RollingEnergyBudget


def _record(task_id: str, age_seconds: float) -> dict:
    return {
        "task_id": task_id,
        "policy": "min_energy",
        "scheduling_policy": "min_energy",
        "substrate": "silicon",
        "energy_cost": 0.1,
        "energy_saved": 0.0,
        "timestamp": time.time() - age_seconds,
    }


def test_plan_retention_purge_validation():
    records = [_record("a", 10)]
    with pytest.raises(ValueError, match="at least one retention criterion"):
        plan_retention_purge(records)
    with pytest.raises(ValueError, match="keep_last must be an integer"):
        plan_retention_purge(records, keep_last=1.5)
    with pytest.raises(ValueError, match="keep_last must be an integer"):
        plan_retention_purge(records, keep_last=False)
    with pytest.raises(ValueError, match="keep_last must be >= 0"):
        plan_retention_purge(records, keep_last=-2)
    with pytest.raises(ValueError, match="older_than_seconds must be positive"):
        plan_retention_purge(records, older_than_seconds=-5)
    with pytest.raises(ValueError, match="older_than_seconds must be a number"):
        plan_retention_purge(records, older_than_seconds=object())


def test_plan_retention_purge_semantics():
    # Records are appended chronologically: oldest first.
    records = [_record(f"r{i}", age) for i, age in enumerate((900, 800, 100, 50))]
    cutoff, protected, removed = plan_retention_purge(records, keep_last=1)
    assert cutoff is None
    assert protected == 1
    assert removed == [0, 1, 2]
    _cutoff, protected, removed = plan_retention_purge(records, older_than_seconds=500)
    assert protected == 0
    assert removed == [0, 1]
    # Union semantics: keep_last=2 protects r2/r3; the age rule keeps r2/r3
    # too (<=500s) -> only the two ancient records go.
    _cutoff, protected, removed = plan_retention_purge(records, keep_last=2, older_than_seconds=20)
    assert protected == 2
    assert removed == [0, 1]


@pytest.fixture()
def scheduler() -> EnergyAwareScheduler:
    engine = SubstrateConvergenceEngine()
    engine.register_substrate("silicon", 5.0, 10.0, 0.1, 100)
    sched = EnergyAwareScheduler(
        engine,
        energy_budget=RollingEnergyBudget(limit=10.0, window_seconds=3600.0),
    )
    for i, age in enumerate((900, 400, 50)):
        sched._dispatches.append(_record(f"d{i}", age))
    return sched


def test_preview_purge_dispatches_dry_run(scheduler):
    preview = scheduler.preview_purge_dispatches(keep_last=1)
    assert preview["dry_run"] is True
    assert preview["total_dispatches"] == 3
    assert preview["would_remove"] == 2
    assert preview["would_remain"] == 1
    assert preview["protected_by_keep_last"] == 1
    assert preview["cutoff_timestamp"] is None
    assert preview["oldest_remaining_timestamp"] is not None
    assert len(scheduler._dispatches) == 3  # untouched


def test_preview_purge_dispatches_older_than(scheduler):
    preview = scheduler.preview_purge_dispatches(older_than_seconds=500)
    assert preview["would_remove"] == 1
    assert preview["would_remain"] == 2


def test_purge_dispatches_mutates_but_keeps_budget_ledger(scheduler):
    scheduler.energy_budget.record(3.0)
    report = scheduler.purge_dispatches(keep_last=1)
    assert report["dry_run"] is False
    assert report["removed"] == 2
    assert report["remaining"] == 1
    assert [d["task_id"] for d in scheduler._dispatches] == ["d2"]
    assert report["purged_at"] > 0
    # Purging history never refunds spend.
    assert scheduler.energy_budget.spent() == pytest.approx(3.0)
    assert scheduler.report()["dispatches"] == 1


def test_purge_dispatches_empty_noop():
    engine = SubstrateConvergenceEngine()
    engine.register_substrate("silicon", 5.0, 10.0, 0.1, 100)
    sched = EnergyAwareScheduler(engine)
    report = sched.purge_dispatches(keep_last=0)
    assert report["removed"] == 0
    assert sched.report()["dispatches"] == 0


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


def _seed_dispatches(client, count: int) -> None:
    for i in range(count):
        resp = client.post(
            "/api/substrate/schedule",
            json={"id": f"sd-{i}", "category": "general", "compute_units": 1, "execute": True},
        )
        assert resp.status_code == 200


def test_endpoint_dispatches_preview_and_validation(client):
    _seed_dispatches(client, 3)
    resp = client.post("/api/substrate/dispatches/preview", json={"keep_last": 2})
    assert resp.status_code == 200
    preview = resp.json()
    assert preview["dry_run"] is True
    assert preview["total_dispatches"] == 3
    assert preview["would_remove"] == 1
    # Scheduler report unchanged.
    assert client.get("/api/substrate/scheduler").json()["dispatches"] == 3
    assert client.post("/api/substrate/dispatches/preview", json={}).status_code == 400
    assert client.post("/api/substrate/dispatches/preview", json={"keep_last": -1}).status_code == 400


def test_endpoint_dispatches_purge_guard_and_effect(client):
    _seed_dispatches(client, 3)
    missing = client.post("/api/substrate/dispatches/purge", json={"keep_last": 1})
    assert missing.status_code == 400
    assert "confirm" in missing.json()["error"]
    assert "preview" in missing.json()["error"]
    assert client.get("/api/substrate/scheduler").json()["dispatches"] == 3
    resp = client.post("/api/substrate/dispatches/purge", json={"confirm": True, "keep_last": 1})
    assert resp.status_code == 200
    report = resp.json()
    assert report["removed"] == 2
    assert report["remaining"] == 1
    assert client.get("/api/substrate/scheduler").json()["dispatches"] == 1


def test_dispatches_purge_leaves_engine_history_intact(client):
    _seed_dispatches(client, 2)
    client.post("/api/substrate/dispatches/purge", json={"confirm": True, "keep_last": 0})
    assert client.get("/api/substrate/scheduler").json()["dispatches"] == 0
    # The engine history is a separate store (purged via its own endpoint).
    assert client.get("/api/substrate/stats").json()["total_dispatches"] == 2


def test_shared_helper_matches_engine_selection():
    # Engine preview delegates to the same shared plan: identical reports
    # for identical criteria.
    engine = SubstrateConvergenceEngine()
    engine.register_substrate("silicon", 5.0, 10.0, 0.1, 100)
    engine.dispatch_history.extend([_record(f"e{i}", age) for i, age in enumerate((900, 100))])
    cutoff, protected, removed = plan_retention_purge(engine.dispatch_history, keep_last=1)
    preview = engine.preview_purge_history(keep_last=1)
    assert preview["would_remove"] == len(removed) == 1
    assert preview["protected_by_keep_last"] == protected == 1
    assert preview["cutoff_timestamp"] == cutoff is None


def test_substrate_page_retention_target_select(client):
    resp = client.get("/substrate")
    assert resp.status_code == 200
    assert 'id="purge-target"' in resp.text
    assert "Scheduler dispatches" in resp.text
    assert "purgeTargetBase()" in resp.text
    assert "/api/substrate/dispatches" in resp.text
