"""Tests for cold-storage archive retention preview + guarded purge (v11.15.0)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.agent_memory_system import AgentMemorySystem, MemoryEntry, MemoryType
from aios_core.dashboard import create_dashboard


def _archived(memory_id: str, days_old: float) -> MemoryEntry:
    return MemoryEntry(
        memory_id=memory_id,
        memory_type=MemoryType.LONG_TERM,
        platform="olx",
        action="parse",
        result="success",
        created_at=time.time() - days_old * 86400,
    )


@pytest.fixture()
def system() -> AgentMemorySystem:
    sys_ = AgentMemorySystem()
    # Chronological append: oldest first — ages 100/50/10/2 days.
    for i, days in enumerate((100.0, 50.0, 10.0, 2.0)):
        sys_._archive.append(_archived(f"a{i}", days))
    return sys_


def test_preview_keep_last_counts(system):
    preview = system.preview_archive_purge(keep_last=2)
    assert preview["dry_run"] is True
    assert preview["archived_total"] == 4
    assert preview["would_remove"] == 2
    assert preview["would_remain"] == 2
    assert preview["protected_by_keep_last"] == 2
    assert preview["cutoff_timestamp"] is None
    assert preview["oldest_remaining_age_days"] == pytest.approx(10.0, abs=0.01)
    assert len(system._archive) == 4  # untouched


def test_preview_older_than_days(system):
    preview = system.preview_archive_purge(older_than_days=30)
    assert preview["would_remove"] == 2  # 100 and 50 day olds
    assert preview["would_remain"] == 2
    assert preview["protected_by_keep_last"] == 0
    assert preview["cutoff_timestamp"] is not None


def test_preview_union_semantics(system):
    # keep_last=1 protects the 2-day-old; the day bound alone (>3d)
    # would remove three — union keeps the 2-day entry only.
    preview = system.preview_archive_purge(keep_last=1, older_than_days=3)
    assert preview["would_remove"] == 3
    assert preview["would_remain"] == 1


def test_purge_validation(system):
    with pytest.raises(ValueError, match="at least one retention criterion"):
        system.preview_archive_purge()
    with pytest.raises(ValueError, match="keep_last must be an integer"):
        system.purge_archive(keep_last=1.5)
    with pytest.raises(ValueError, match="older_than_days must be a number"):
        system.purge_archive(older_than_days="old")
    with pytest.raises(ValueError, match="older_than_days must be positive"):
        system.purge_archive(older_than_days=0)


def test_purge_removes_and_reports(system):
    report = system.purge_archive(older_than_days=30)
    assert report["dry_run"] is False
    assert report["removed"] == 2
    assert report["removed_ids"] == ["a0", "a1"]
    assert report["remaining"] == 2
    assert report["purged_at"] > 0
    assert [e.memory_id for e in system._archive] == ["a2", "a3"]
    assert system.preview_archive_purge(older_than_days=30)["would_remove"] == 0


def test_purge_empty_archive_noop():
    sys_ = AgentMemorySystem()
    report = sys_.purge_archive(keep_last=0)
    assert report["removed"] == 0
    assert report["remaining"] == 0


@pytest.fixture()
def client():
    dashboard_module._memory_system = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.15.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._memory_system = None


def _seed_archive(count: int) -> None:
    system = dashboard_module._get_memory_system()
    system._archive.extend(_archived(f"seed-{i}", float(50 + i)) for i in range(count))


def test_endpoint_preview_and_validation(client):
    _seed_archive(3)
    resp = client.post("/api/memory/archive/purge/preview", json={"keep_last": 1})
    assert resp.status_code == 200
    preview = resp.json()
    assert preview["dry_run"] is True
    assert preview["archived_total"] == 3
    assert preview["would_remove"] == 2
    # Read-only: archive stats unchanged.
    assert client.get("/api/memory/archive").json()["archived_total"] == 3
    assert client.post("/api/memory/archive/purge/preview", json={}).status_code == 400
    bad = client.post("/api/memory/archive/purge/preview", json={"older_than_days": -1})
    assert bad.status_code == 400
    assert "older_than_days" in bad.json()["error"]


def test_endpoint_purge_guard_and_effect(client):
    _seed_archive(3)
    missing = client.post("/api/memory/archive/purge", json={"keep_last": 1})
    assert missing.status_code == 400
    assert "confirm" in missing.json()["error"]
    assert "purge/preview" in missing.json()["error"]
    assert client.get("/api/memory/archive").json()["archived_total"] == 3
    resp = client.post("/api/memory/archive/purge", json={"confirm": True, "keep_last": 1})
    assert resp.status_code == 200
    report = resp.json()
    assert report["removed"] == 2
    assert report["remaining"] == 1
    assert client.get("/api/memory/archive").json()["archived_total"] == 1
    # Active pools untouched by the archive purge.
    stats = client.get("/api/memory/stats").json()
    assert stats["long_term_count"] == 3


def test_memory_page_has_archive_purge_controls(client):
    resp = client.get("/memory")
    assert resp.status_code == 200
    assert 'id="arch-purge-keep"' in resp.text
    assert 'id="arch-purge-age"' in resp.text
    assert "runArchivePurgePreview()" in resp.text
    assert "runArchivePurge()" in resp.text
    assert "/api/memory/archive/purge/preview" in resp.text
