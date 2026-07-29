"""Tests for the cold-storage memory archive + its dashboard APIs (v11.7.0)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.agent_memory_system import AgentMemorySystem, MemoryType
from aios_core.dashboard import create_dashboard

TEN_DAYS_AGO = time.time() - 10 * 86400


def _aged(
    system: AgentMemorySystem, platform: str, *, confidence: float = 1.0, decay_rate: float = 0.9, access_count: int = 0
):
    """Record a long-term entry that is 10 days old."""
    entry = system.record(
        platform, "collect", "success", memory_type=MemoryType.LONG_TERM, confidence=confidence, decay_rate=decay_rate
    )
    entry.created_at = TEN_DAYS_AGO
    entry.access_count = access_count
    return entry


def test_archive_dead_validation():
    system = AgentMemorySystem()
    with pytest.raises(ValueError):
        system.archive_dead(min_strength=-0.1)
    with pytest.raises(ValueError):
        system.archive_dead(min_age_days=-1)


def test_archive_moves_only_dead_entries():
    system = AgentMemorySystem()
    dead = _aged(system, "old-weak")  # strength ~0.0001 after decay
    _aged(system, "old-but-used", access_count=50)  # +0.3 access boost → strong
    fresh_weak = system.record(
        "fresh-weak", "collect", "success", memory_type=MemoryType.LONG_TERM, confidence=0.01, decay_rate=0.9
    )  # weak but age 0 → age-gated
    system.record("fresh-strong", "collect", "success", memory_type=MemoryType.LONG_TERM)

    report = system.archive_dead(min_strength=0.05, min_age_days=1.0)
    assert report["archived"] == 1
    assert report["archived_ids"] == [dead.memory_id]
    remaining = {e.platform for e in system._long_term}
    assert remaining == {"old-but-used", "fresh-weak", "fresh-strong"}
    assert fresh_weak.memory_id not in report["archived_ids"]  # age gate held


def test_archive_cleans_compressed_index():
    system = AgentMemorySystem()
    dead = _aged(system, "old-weak")
    _aged(system, "old-but-used", access_count=50)
    system.optimize_storage()
    assert dead.memory_id in system._compressed
    system.archive_dead()
    assert dead.memory_id not in system._compressed


def test_archive_idempotent():
    system = AgentMemorySystem()
    _aged(system, "old-weak")
    first = system.archive_dead()
    assert first["archived"] == 1
    second = system.archive_dead()
    assert second["archived"] == 0
    assert system.archive_stats()["archived_total"] == 1


def test_archived_entries_leave_active_recall():
    system = AgentMemorySystem()
    dead = _aged(system, "dead-platform")
    system.record("live-platform", "collect", "success", memory_type=MemoryType.LONG_TERM)
    system.archive_dead()

    recalled = system.recall()
    platforms = {e.platform for e in recalled}
    assert "dead-platform" not in platforms
    assert "live-platform" in platforms

    archived = system.archived(limit=10)
    assert [e["memory_id"] for e in archived] == [dead.memory_id]
    assert archived[0]["platform"] == "dead-platform"

    # Compressed recall cannot resurrect archived memories either
    recalled_c = system.recall_compressed("dead-platform collect success", top_k=5)
    assert all(e.platform != "dead-platform" for e in recalled_c)


def test_stats_exposes_archive_block():
    system = AgentMemorySystem()
    _aged(system, "old-weak")
    system.archive_dead()
    stats = system.stats()
    assert stats["archive"]["archived_total"] == 1
    assert stats["archive"]["last_report"]["archived"] == 1
    # fresh pools untouched: long_term count dropped by the archived entry
    assert stats["long_term_count"] == 0


# ------------------------------------------------------------------
# Dashboard APIs
# ------------------------------------------------------------------


@pytest.fixture()
def client():
    dashboard_module._memory_system = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.6.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._memory_system = None


def test_archive_api_empty_by_default(client):
    data = client.get("/api/memory/archive").json()
    assert data["archived_total"] == 0
    assert data["entries"] == []


def test_archive_run_api_lifecycle(client):
    system = dashboard_module._get_memory_system()
    dead = system.record("aged", "collect", "success", memory_type=MemoryType.LONG_TERM, decay_rate=0.9)
    dead.created_at = TEN_DAYS_AGO

    report = client.post("/api/memory/archive/run", json={}).json()
    assert report["archived"] == 1
    assert report["archived_ids"] == [dead.memory_id]

    listing = client.get("/api/memory/archive?limit=5").json()
    assert listing["archived_total"] == 1
    assert listing["entries"][0]["platform"] == "aged"

    # Second run: nothing left to archive (idempotent)
    again = client.post("/api/memory/archive/run", json={}).json()
    assert again["archived"] == 0


def test_archive_run_api_param_validation(client):
    bad_type = client.post("/api/memory/archive/run", json={"min_strength": "abc"})
    assert bad_type.status_code == 400
    negative = client.post("/api/memory/archive/run", json={"min_age_days": -5})
    assert negative.status_code == 400
    # Explicit params do affect behaviour: min_age_days=10.5 spares a 10-day-old entry
    system = dashboard_module._get_memory_system()
    dead = system.record("aged", "collect", "success", memory_type=MemoryType.LONG_TERM, decay_rate=0.9)
    dead.created_at = TEN_DAYS_AGO
    spared = client.post("/api/memory/archive/run", json={"min_age_days": 10.5}).json()
    assert spared["archived"] == 0
    strict = client.post("/api/memory/archive/run", json={"min_age_days": 1.0, "min_strength": 0.9}).json()
    assert strict["archived"] == 1


def test_memory_page_has_archive_wiring(client):
    resp = client.get("/memory")
    assert resp.status_code == 200
    assert "archived-total" in resp.text
    assert "v11.10.0" in resp.text
