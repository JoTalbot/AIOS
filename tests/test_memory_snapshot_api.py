"""Tests for the memory snapshot save/load endpoints + persistence panel (v11.8.0)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.agent_memory_system import MemoryType
from aios_core.dashboard import create_dashboard


@pytest.fixture()
def client():
    dashboard_module._memory_system = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.8.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._memory_system = None


def test_snapshot_save_and_load_roundtrip(client, tmp_path):
    path = tmp_path / "snap.json"
    resp = client.post("/api/memory/snapshot/save", json={"path": str(path)})
    assert resp.status_code == 200
    data = resp.json()
    assert data["saved"] == str(path)
    # Seeded singleton: 3 long-term + 4 episodic entries, >= 1 pattern.
    assert data["totals"]["long_term"] == 3
    assert data["totals"]["episodic"] == 4
    assert data["totals"]["archived"] == 0
    assert path.is_file()
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk["format"] == 1

    # Mutate the live system, then load the snapshot back over it.
    system = dashboard_module._memory_system
    system.record("prom", "login", "success", memory_type=MemoryType.LONG_TERM)
    assert system.stats()["long_term_count"] == 4

    resp = client.post("/api/memory/snapshot/load", json={"path": str(path)})
    assert resp.status_code == 200
    report = resp.json()
    assert report["loaded"] == str(path)
    assert report["long_term"] == 3
    assert report["episodic"] == 4
    # Live state was fully replaced by the snapshot.
    assert system.stats()["long_term_count"] == 3
    assert system.stats()["episodic_count"] == 4


def test_snapshot_default_path(client, monkeypatch, tmp_path):
    default = tmp_path / "default.json"
    monkeypatch.setattr(dashboard_module, "_MEMORY_SNAPSHOT_PATH", default)
    resp = client.post("/api/memory/snapshot/save", json={})
    assert resp.status_code == 200
    assert resp.json()["saved"] == str(default)
    assert default.is_file()
    # Load with no body hits the same default location.
    resp = client.post("/api/memory/snapshot/load", json={})
    assert resp.status_code == 200
    assert resp.json()["loaded"] == str(default)


def test_snapshot_load_missing_file(client, tmp_path):
    resp = client.post("/api/memory/snapshot/load", json={"path": str(tmp_path / "absent.json")})
    assert resp.status_code == 404
    assert "snapshot not found" in resp.json()["error"]


def test_snapshot_load_corrupt_file(client, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    resp = client.post("/api/memory/snapshot/load", json={"path": str(bad)})
    assert resp.status_code == 400
    assert "snapshot load failed" in resp.json()["error"]

    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps({"format": 999, "pools": {}}), encoding="utf-8")
    resp = client.post("/api/memory/snapshot/load", json={"path": str(wrong)})
    assert resp.status_code == 400


def test_snapshot_bad_bodies(client, tmp_path):
    not_json = client.post("/api/memory/snapshot/save", content="[1,2]", headers={"Content-Type": "application/json"})
    assert not_json.status_code == 400
    assert client.post("/api/memory/snapshot/save", json={"path": 123}).status_code == 400
    assert client.post("/api/memory/snapshot/save", json={"path": "   "}).status_code == 400
    assert client.post("/api/memory/snapshot/load", json={"path": 4.5}).status_code == 400


def test_memory_page_has_persistence_panel(client):
    resp = client.get("/memory")
    assert resp.status_code == 200
    assert "Snapshot Persistence" in resp.text
    assert "/api/memory/snapshot/" in resp.text  # save/load base path used by runSnapshot()
    assert "snap-path" in resp.text
