"""Tests for dispatch-history retention preview + guarded purge (v11.13.0)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.dashboard import create_dashboard
from aios_core.substrate_convergence import SubstrateConvergenceEngine


@pytest.fixture()
def engine() -> SubstrateConvergenceEngine:
    eng = SubstrateConvergenceEngine()
    eng.register_substrate(
        "silicon",
        latency_base_ms=5.0,
        efficiency_gflops_per_watt=10.0,
        energy_cost_per_unit=0.1,
        capacity=100,
    )
    now = time.time()
    # 6 records, oldest first: ages 1000, 900, ..., 500 seconds.
    for i in range(6):
        eng.dispatch_history.append(
            {
                "task_id": f"t{i}",
                "selected_substrate": "silicon",
                "energy_cost": 0.1,
                "timestamp": now - (1000 - i * 100),
            }
        )
    return eng


def test_preview_keep_last_counts(engine):
    preview = engine.preview_purge_history(keep_last=2)
    assert preview["dry_run"] is True
    assert preview["total_records"] == 6
    assert preview["would_remove"] == 4
    assert preview["would_remain"] == 2
    assert preview["protected_by_keep_last"] == 2
    assert preview["cutoff_timestamp"] is None
    assert preview["oldest_remaining_timestamp"] is not None
    # Pure dry-run: history untouched.
    assert len(engine.dispatch_history) == 6


def test_preview_older_than(engine):
    preview = engine.preview_purge_history(older_than_seconds=750)
    # Ages 1000/900/800 are older than 750s; 700/600/500 survive.
    assert preview["would_remove"] == 3
    assert preview["would_remain"] == 3
    assert preview["protected_by_keep_last"] == 0
    assert preview["cutoff_timestamp"] is not None
    assert len(engine.dispatch_history) == 6


def test_preview_both_criteria_keep_union(engine):
    # keep_last=2 protects the two newest; age cutoff 150s would remove
    # everything except the newest (~500s ago) — union keeps 3 records.
    preview = engine.preview_purge_history(keep_last=3, older_than_seconds=150)
    assert preview["would_remove"] == 3
    assert preview["would_remain"] == 3


def test_preview_validation(engine):
    with pytest.raises(ValueError, match="at least one retention criterion"):
        engine.preview_purge_history()
    with pytest.raises(ValueError, match="keep_last must be an integer"):
        engine.preview_purge_history(keep_last=2.5)
    with pytest.raises(ValueError, match="keep_last must be an integer"):
        engine.preview_purge_history(keep_last=True)
    with pytest.raises(ValueError, match="keep_last must be >= 0"):
        engine.preview_purge_history(keep_last=-1)
    with pytest.raises(ValueError, match="older_than_seconds must be positive"):
        engine.preview_purge_history(older_than_seconds=0)
    with pytest.raises(ValueError, match="older_than_seconds must be a number"):
        engine.preview_purge_history(older_than_seconds="soon")


def test_purge_mutates_and_reports(engine):
    report = engine.purge_history(keep_last=2)
    assert report["dry_run"] is False
    assert report["removed"] == 4
    assert report["remaining"] == 2
    assert report["keep_last"] == 2
    assert report["purged_at"] > 0
    assert [r["task_id"] for r in engine.dispatch_history] == ["t4", "t5"]
    # Mirrors the preview selection exactly.
    assert engine.preview_purge_history(keep_last=2)["would_remove"] == 0


def test_purge_empty_history_is_noop():
    eng = SubstrateConvergenceEngine()
    report = eng.purge_history(keep_last=10)
    assert report["removed"] == 0
    assert report["remaining"] == 0
    assert report["protected_by_keep_last"] == 0


def test_purge_keep_last_zero_wipes_everything(engine):
    report = engine.purge_history(keep_last=0)
    assert report["removed"] == 6
    assert engine.dispatch_history == []


@pytest.fixture()
def client():
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.13.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None


def _seed_dispatches(client, count: int) -> None:
    for i in range(count):
        resp = client.post(
            "/api/substrate/schedule",
            json={"id": f"purge-{i}", "category": "general", "compute_units": 1, "execute": True},
        )
        assert resp.status_code == 200


def test_endpoint_preview_shape_and_no_mutation(client):
    _seed_dispatches(client, 3)
    resp = client.post("/api/substrate/history/preview", json={"keep_last": 1})
    assert resp.status_code == 200
    preview = resp.json()
    assert preview["dry_run"] is True
    assert preview["total_records"] == 3
    assert preview["would_remove"] == 2
    assert preview["would_remain"] == 1
    # Nothing was deleted.
    assert len(client.get("/api/substrate/history").json()["history"]) == 3


def test_endpoint_preview_validation(client):
    assert client.post("/api/substrate/history/preview", json={}).status_code == 400
    resp = client.post("/api/substrate/history/preview", json={"keep_last": -1})
    assert resp.status_code == 400
    assert "keep_last" in resp.json()["error"]


def test_endpoint_purge_requires_confirm(client):
    _seed_dispatches(client, 2)
    missing = client.post("/api/substrate/history/purge", json={"keep_last": 1})
    assert missing.status_code == 400
    assert "confirm" in missing.json()["error"]
    assert "preview" in missing.json()["error"]
    assert client.post("/api/substrate/history/purge", json={"confirm": True}).status_code == 400
    # Guarded endpoint deletes nothing when confirm is missing.
    assert len(client.get("/api/substrate/history").json()["history"]) == 2


def test_endpoint_purge_deletes(client):
    _seed_dispatches(client, 3)
    resp = client.post("/api/substrate/history/purge", json={"confirm": True, "keep_last": 1})
    assert resp.status_code == 200
    report = resp.json()
    assert report["dry_run"] is False
    assert report["removed"] == 2
    assert report["remaining"] == 1
    history = client.get("/api/substrate/history").json()["history"]
    assert [r["task_id"] for r in history] == ["purge-2"]
    assert client.get("/api/substrate/stats").json()["total_dispatches"] == 1


def test_substrate_page_has_retention_and_budget_panels(client):
    resp = client.get("/substrate")
    assert resp.status_code == 200
    assert 'id="purge-keep"' in resp.text
    assert 'id="purge-age"' in resp.text
    assert "runHistoryPreview()" in resp.text
    assert "runHistoryPurge()" in resp.text
    assert 'id="budget-limit-input"' in resp.text
    assert 'id="budget-window-input"' in resp.text
    assert "runBudgetApply()" in resp.text
    assert "/api/substrate/history" in resp.text
    assert "/api/substrate/budget" in resp.text
