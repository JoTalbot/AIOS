"""Tests for snapshot rotation keep_rotated + file listing (v11.15.0)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.agent_memory_system import AgentMemorySystem, MemoryEntry, MemoryType
from aios_core.dashboard import create_dashboard


@pytest.fixture()
def system() -> AgentMemorySystem:
    sys_ = AgentMemorySystem()
    sys_._long_term.append(
        MemoryEntry(
            memory_id="rot-1",
            memory_type=MemoryType.LONG_TERM,
            platform="olx",
            action="parse",
            result="success",
        )
    )
    return sys_


def test_save_default_has_no_rotation(system, tmp_path):
    target = tmp_path / "snap.json"
    report = system.save(str(target))
    assert "rotation" not in report
    system.save(str(target))
    system.save(str(target))
    # No rotated files created without keep_rotated.
    assert AgentMemorySystem.list_snapshot_files(str(target)) == [
        {"path": str(target), "rotation": 0, "size_bytes": target.stat().st_size, "modified_at": target.stat().st_mtime}
    ]


def test_rotation_shifts_and_drops(system, tmp_path):
    target = tmp_path / "snap.json"
    for _ in range(4):
        report = system.save(str(target), keep_rotated=2)
    rotation = report["rotation"]
    assert rotation["keep_rotated"] == 2
    assert rotation["rotated"] == 2
    assert len(rotation["dropped"]) == 1
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ["snap.1.json", "snap.2.json", "snap.json"]

    # Each rotation is a valid loadable snapshot.
    restored = AgentMemorySystem()
    restored.load(str(tmp_path / "snap.1.json"))
    assert any(e.memory_id == "rot-1" for e in restored._long_term)


def test_rotation_start_from_fresh(system, tmp_path):
    target = tmp_path / "snap.json"
    first = system.save(str(target), keep_rotated=3)
    assert first["rotation"] == {"keep_rotated": 3, "rotated": 0, "dropped": []}
    second = system.save(str(target), keep_rotated=3)
    assert second["rotation"]["rotated"] == 1
    assert (tmp_path / "snap.1.json").exists()


def test_save_keep_rotated_validation(system, tmp_path):
    target = tmp_path / "snap.json"
    with pytest.raises(ValueError, match="keep_rotated must be an integer"):
        system.save(str(target), keep_rotated=True)
    with pytest.raises(ValueError, match="keep_rotated must be an integer"):
        system.save(str(target), keep_rotated=1.5)
    with pytest.raises(ValueError, match="between 0 and 50"):
        system.save(str(target), keep_rotated=-1)
    with pytest.raises(ValueError, match="between 0 and 50"):
        system.save(str(target), keep_rotated=99)
    assert not target.exists()  # failed validation writes nothing


def test_list_snapshot_files_ordering_and_gaps(system, tmp_path):
    target = tmp_path / "snap.json"
    system.save(str(target), keep_rotated=3)
    system.save(str(target), keep_rotated=3)
    # Delete .1 to prove listing tolerates rotation gaps.
    (tmp_path / "snap.1.json").unlink()
    system.save(str(target), keep_rotated=3)
    files = AgentMemorySystem.list_snapshot_files(str(target))
    rotations = [f["rotation"] for f in files]
    assert rotations[0] == 0  # live first
    assert rotations == sorted(rotations)
    assert all(f["size_bytes"] > 0 and f["modified_at"] > 0 for f in files)
    assert AgentMemorySystem.list_snapshot_files(str(tmp_path / "absent.json")) == []


@pytest.fixture()
def client():
    dashboard_module._memory_system = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.15.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._memory_system = None


def test_endpoint_save_with_rotation_and_list(client, tmp_path):
    target = str(tmp_path / "snap.json")
    for _ in range(3):
        resp = client.post("/api/memory/snapshot/save", json={"path": target, "keep_rotated": 1})
        assert resp.status_code == 200
    report = resp.json()
    assert report["rotation"]["keep_rotated"] == 1
    assert report["totals"]["long_term"] >= 1

    listing = client.get("/api/memory/snapshot/list", params={"path": target})
    assert listing.status_code == 200
    data = listing.json()
    assert data["file_count"] == 2
    assert [f["rotation"] for f in data["files"]] == [0, 1]

    # Loading the rotated copy restores state too.
    rotated = data["files"][1]["path"]
    load = client.post("/api/memory/snapshot/load", json={"path": rotated})
    assert load.status_code == 200


def test_endpoint_save_keep_rotated_validation(client, tmp_path):
    target = str(tmp_path / "snap.json")
    resp = client.post("/api/memory/snapshot/save", json={"path": target, "keep_rotated": "two"})
    assert resp.status_code == 400
    assert "keep_rotated" in resp.json()["error"]
    resp = client.post("/api/memory/snapshot/save", json={"path": target, "keep_rotated": 500})
    assert resp.status_code == 400
    # Plain save without keep_rotated keeps the pre-v11.15 behaviour.
    assert client.post("/api/memory/snapshot/save", json={"path": target}).status_code == 200
    assert "rotation" not in client.post("/api/memory/snapshot/save", json={"path": target}).json()


def test_endpoint_list_default_path(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_module, "_MEMORY_SNAPSHOT_PATH", tmp_path / "memory_snapshot.json")
    resp = client.get("/api/memory/snapshot/list")
    assert resp.status_code == 200
    assert resp.json()["file_count"] == 0  # nothing saved yet
    client.post("/api/memory/snapshot/save", json={})
    assert client.get("/api/memory/snapshot/list").json()["file_count"] == 1


def test_memory_page_has_rotation_controls(client):
    resp = client.get("/memory")
    assert resp.status_code == 200
    assert 'id="snap-keep-rotated"' in resp.text
    assert "runSnapshotList()" in resp.text
    assert "/api/memory/snapshot/list" in resp.text
