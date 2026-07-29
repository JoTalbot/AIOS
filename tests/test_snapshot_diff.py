"""Tests for live-vs-snapshot diff + endpoint + panel button (v11.12.0)."""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.agent_memory_system import AgentMemorySystem, MemoryType
from aios_core.dashboard import create_dashboard


@pytest.fixture()
def system() -> AgentMemorySystem:
    s = AgentMemorySystem()
    s.record("olx", "login", "success", memory_type=MemoryType.LONG_TERM)
    s.record("olx", "collect", "success", memory_type=MemoryType.LONG_TERM)
    return s


def test_diff_identical_to_own_snapshot(system):
    report = system.diff_snapshot(system.snapshot())
    assert report["identical"] is True
    assert report["added"] == {"short_term": [], "long_term": [], "episodic": [], "archive": []}
    assert report["removed"] == report["added"]
    assert report["changed"] == report["added"]
    assert report["counts"]["live"] == report["counts"]["snapshot"]
    assert report["patterns_added"] == []
    assert report["metadata_drift"]["dedup_threshold"]["live"] == 0.92


def test_diff_detects_added_entries(system):
    snap = system.snapshot()
    system.record("prom", "login", "success", memory_type=MemoryType.LONG_TERM)
    report = system.diff_snapshot(snap)
    assert report["identical"] is False
    assert report["added"]["long_term"] == ["mem_3"]
    assert report["removed"] == {"short_term": [], "long_term": [], "episodic": [], "archive": []}
    assert report["counts"]["live"]["long_term"] == 3
    assert report["counts"]["snapshot"]["long_term"] == 2


def test_diff_detects_removed_and_changed():
    system = AgentMemorySystem()
    system.record("olx", "login", "success", memory_type=MemoryType.LONG_TERM)
    system.record("olx", "login", "success", memory_type=MemoryType.LONG_TERM)  # identical pair
    snap = system.snapshot()
    system._long_term[0].access_count += 5  # mutate one member in place
    system.deduplicate(threshold=0.92)
    report = system.diff_snapshot(snap)
    assert report["identical"] is False
    # The identical pair merged: one id left the live LT pool.
    assert len(report["removed"]["long_term"]) == 1
    survivor = system._long_term[0].memory_id
    # The survivor absorbed the +5 access counts via the merge ->
    # it shows up as CHANGED against the snapshot copy.
    assert survivor in report["changed"]["long_term"]
    assert report["metadata_drift"]["dedup_removed_total"]["live"] == 1
    assert report["metadata_drift"]["dedup_removed_total"]["snapshot"] == 0


def test_diff_detects_pattern_drift(system):
    snap = system.snapshot()
    for i in range(3):
        system.record("olx", "collect", "success", memory_type=MemoryType.EPISODIC, context={"i": i})
    system.extract_patterns()
    report = system.diff_snapshot(snap)
    assert report["patterns_added"]
    assert report["patterns_removed"] == []


def test_diff_ignores_decay_drift(system):
    # Strength is DERIVED from created_at at read time: entries ageing on
    # the wall clock never alter persisted fields, so the diff compares
    # snapshot serialisation which deliberately excludes strength.
    assert "strength" not in system._entry_snapshot(system._long_term[0])
    time.sleep(0.01)  # entries age passively; nothing is recorded
    report = system.diff_snapshot(system.snapshot())
    assert report["changed"] == {"short_term": [], "long_term": [], "episodic": [], "archive": []}
    assert report["identical"] is True


def test_diff_validation(system):
    with pytest.raises(ValueError, match="pools"):
        system.diff_snapshot({})
    with pytest.raises(ValueError, match="must be a dict"):
        system.diff_snapshot({"pools": []})
    with pytest.raises(ValueError, match="missing 'archive'"):
        system.diff_snapshot({"pools": {"short_term": [], "long_term": [], "episodic": []}})


# ----------------------------------------------------------------------
# Dashboard endpoint + panel button
# ----------------------------------------------------------------------


@pytest.fixture()
def client():
    dashboard_module._memory_system = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.12.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._memory_system = None


def test_diff_endpoint_roundtrip(client, tmp_path):
    path = tmp_path / "snap.json"
    client.post("/api/memory/snapshot/save", json={"path": str(path)})
    fresh = client.post("/api/memory/snapshot/diff", json={"path": str(path)})
    assert fresh.status_code == 200
    assert fresh.json()["identical"] is True
    assert fresh.json()["path"] == str(path)

    # Live state drifts: new memory recorded after the save.
    system = dashboard_module._memory_system
    system.record("prom", "login", "success", memory_type=MemoryType.LONG_TERM)
    drift = client.post("/api/memory/snapshot/diff", json={"path": str(path)}).json()
    assert drift["identical"] is False
    assert len(drift["added"]["long_term"]) == 1
    assert drift["counts"]["live"]["long_term"] == 4
    assert drift["counts"]["snapshot"]["long_term"] == 3
    # Diff is read-only: a repeat call reports the same drift.
    assert client.post("/api/memory/snapshot/diff", json={"path": str(path)}).json() == drift


def test_diff_endpoint_missing_and_corrupt(client, tmp_path):
    missing = client.post("/api/memory/snapshot/diff", json={"path": str(tmp_path / "no.json")})
    assert missing.status_code == 404
    bad = tmp_path / "bad.json"
    bad.write_text("{oops", encoding="utf-8")
    assert client.post("/api/memory/snapshot/diff", json={"path": str(bad)}).status_code == 400
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps({"format": 1}), encoding="utf-8")
    assert client.post("/api/memory/snapshot/diff", json={"path": str(wrong)}).status_code == 400
    assert client.post("/api/memory/snapshot/diff", json={"path": 5}).status_code == 400


def test_memory_page_has_diff_button(client):
    resp = client.get("/memory")
    assert "/api/memory/snapshot/diff" in resp.text
    assert "runSnapshotDiff" in resp.text
