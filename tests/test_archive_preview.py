"""Tests for archive_dead() dry-run preview + endpoint + panel (v11.11.0)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.agent_memory_system import AgentMemorySystem, MemoryType
from aios_core.dashboard import create_dashboard


def _seed_with_dead() -> AgentMemorySystem:
    """3 LT entries: one dead (fast-decaying, old), two alive (fresh)."""
    system = AgentMemorySystem()
    system.record("olx", "login", "success", memory_type=MemoryType.LONG_TERM)
    system.record("olx", "collect", "success", memory_type=MemoryType.LONG_TERM)
    system.record("prom", "login", "success", memory_type=MemoryType.LONG_TERM)
    dead = system._long_term[-1]
    dead.decay_rate = 1.0
    dead.created_at = time.time() - 10 * 86400  # 10 days old
    return system


def test_preview_parity_with_real_archive():
    system = _seed_with_dead()
    preview = system.preview_archive_dead(min_strength=0.05, min_age_days=1.0)
    assert preview["dry_run"] is True
    assert preview["would_archive"] == 1
    assert preview["entries"][0]["memory_id"].startswith("mem_")
    assert preview["entries"][0]["age_days"] >= 9.9
    assert preview["counts_after"] == {"long_term": 2, "archive": 1}

    # Preview alone moved nothing.
    assert system.stats()["long_term_count"] == 3
    assert system.archive_stats()["archived_total"] == 0

    # The real archive_dead() moves exactly the previewed ids.
    report = system.archive_dead(min_strength=0.05, min_age_days=1.0)
    assert report["archived_ids"] == [preview["entries"][0]["memory_id"]]
    assert system.stats()["long_term_count"] == preview["counts_after"]["long_term"]
    assert system.archive_stats()["archived_total"] == preview["counts_after"]["archive"]


def test_preview_counts_existing_archive():
    system = _seed_with_dead()
    system.archive_dead(min_strength=0.05, min_age_days=1.0)  # move the dead one for real
    # Make the second entry dead as well.
    second = system._long_term[1]
    second.decay_rate = 1.0
    second.created_at = time.time() - 5 * 86400
    preview = system.preview_archive_dead(min_strength=0.05, min_age_days=1.0)
    assert preview["would_archive"] == 1
    assert preview["counts_after"] == {"long_term": 1, "archive": 2}


def test_preview_respects_age_floor():
    system = AgentMemorySystem()
    system.record("olx", "login", "success", memory_type=MemoryType.LONG_TERM)
    entry = system._long_term[0]
    entry.decay_rate = 1.0
    entry.created_at = time.time() - 3600  # weak-ish? No: fresh but fast decay
    # 1h old, exp(-1.0/24) ≈ 0.959 -> strength above 0.05 anyway; assert by age floor:
    entry.confidence = 0.01  # strength 0.01*exp(-...) < 0.05, but only 1 hour old
    preview = system.preview_archive_dead(min_strength=0.05, min_age_days=1.0)
    assert preview["would_archive"] == 0  # weak but too young
    older = system.preview_archive_dead(min_strength=0.05, min_age_days=0.01)
    assert older["would_archive"] == 1


def test_preview_validates_arguments():
    system = AgentMemorySystem()
    with pytest.raises(ValueError, match="min_strength"):
        system.preview_archive_dead(min_strength=-0.1)
    with pytest.raises(ValueError, match="min_age_days"):
        system.preview_archive_dead(min_age_days=-1)


# ----------------------------------------------------------------------
# Dashboard endpoint + panel button
# ----------------------------------------------------------------------


@pytest.fixture()
def client():
    dashboard_module._memory_system = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.11.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._memory_system = None


def test_archive_preview_endpoint_shape(client):
    resp = client.post("/api/memory/archive/preview", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["dry_run"] is True
    assert data["min_strength"] == 0.05
    assert data["min_age_days"] == 1.0
    # Seeded singleton is fresh and strong: nothing is dead.
    assert data["would_archive"] == 0
    assert data["counts_after"] == {"long_term": 3, "archive": 0}


def test_archive_preview_endpoint_finds_dead(client):
    system = dashboard_module._get_memory_system()
    dead = system._long_term[0]
    dead.decay_rate = 1.0
    dead.created_at = time.time() - 10 * 86400
    resp = client.post("/api/memory/archive/preview", json={"min_strength": 0.1, "min_age_days": 1.0})
    data = resp.json()
    assert data["would_archive"] == 1
    assert data["counts_after"]["long_term"] == 2
    # Still a preview: archive stays empty until the real run.
    assert client.get("/api/memory/archive").json()["archived_total"] == 0


def test_archive_preview_endpoint_validation(client):
    assert client.post("/api/memory/archive/preview", json={"min_strength": -1}).status_code == 400
    assert client.post("/api/memory/archive/preview", json={"min_age_days": -0.5}).status_code == 400
    assert client.post("/api/memory/archive/preview", json={"min_strength": "x"}).status_code == 400
    bad = client.post("/api/memory/archive/preview", content="[1]", headers={"Content-Type": "application/json"})
    assert bad.status_code == 400


def test_memory_page_has_archive_preview_button(client):
    resp = client.get("/memory")
    assert "/api/memory/archive/preview" in resp.text
    assert "runArchivePreview" in resp.text
