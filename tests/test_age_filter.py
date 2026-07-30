"""Tests for the max_age_days filter in recall/search + endpoint (v11.14.0)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.agent_memory_system import AgentMemorySystem, MemoryEntry, MemoryType
from aios_core.dashboard import create_dashboard


def _entry(memory_id: str, days_old: float, action: str = "parse") -> MemoryEntry:
    return MemoryEntry(
        memory_id=memory_id,
        memory_type=MemoryType.LONG_TERM,
        platform="olx",
        action=action,
        result="success",
        created_at=time.time() - days_old * 86400,
    )


@pytest.fixture()
def system() -> AgentMemorySystem:
    sys_ = AgentMemorySystem()
    sys_._long_term.extend([_entry("fresh", 1.0), _entry("middle", 10.0), _entry("ancient", 400.0)])
    return sys_


def test_recall_max_age_days_filters_old_entries(system):
    everything = system.recall(memory_type=MemoryType.LONG_TERM, min_strength=0.0)
    assert {e.memory_id for e in everything} == {"fresh", "middle", "ancient"}
    recent = system.recall(memory_type=MemoryType.LONG_TERM, min_strength=0.0, max_age_days=30)
    assert {e.memory_id for e in recent} == {"fresh", "middle"}
    strict = system.recall(memory_type=MemoryType.LONG_TERM, min_strength=0.0, max_age_days=5)
    assert {e.memory_id for e in strict} == {"fresh"}
    none = system.recall(memory_type=MemoryType.LONG_TERM, min_strength=0.0, max_age_days=0)
    assert none == []


def test_recall_max_age_days_validation(system):
    with pytest.raises(ValueError, match="max_age_days must be >= 0"):
        system.recall(max_age_days=-1)
    with pytest.raises(ValueError, match="max_age_days must be a number"):
        system.recall(max_age_days="old")
    # None keeps the previous behaviour exactly.
    assert len(system.recall(min_strength=0.0, max_age_days=None)) == 3


def test_search_max_age_days_prefilters_candidates(system):
    all_hits = system.search("olx parse", limit=10)
    assert {h["memory_id"] for h in all_hits} == {"fresh", "middle", "ancient"}
    recent = system.search("olx parse", limit=10, max_age_days=30)
    assert {h["memory_id"] for h in recent} == {"fresh", "middle"}
    assert all("score" in hit for hit in recent)
    assert system.search("olx parse", limit=10, max_age_days=0) == []


def test_search_max_age_days_validation(system):
    with pytest.raises(ValueError, match="max_age_days must be >= 0"):
        system.search("olx", max_age_days=-0.5)
    with pytest.raises(ValueError, match="max_age_days must be a number"):
        system.search("olx", max_age_days="many")


@pytest.fixture()
def client():
    dashboard_module._memory_system = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.14.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._memory_system = None


def test_recall_endpoint_keyword_mode_max_age_days(client):
    base = client.get("/api/memory/recall?q=olx&mode=keyword&top_k=10")
    assert base.status_code == 200
    base_results = base.json()["results"]
    assert base_results  # seeded system has matching entries
    filtered = client.get("/api/memory/recall?q=olx&mode=keyword&top_k=10&max_age_days=30")
    assert filtered.status_code == 200
    # Seeded entries are created at dashboard start (age ~0): all survive 30d.
    assert len(filtered.json()["results"]) == len(base_results)
    none = client.get("/api/memory/recall?q=olx&mode=keyword&top_k=10&max_age_days=0")
    assert none.status_code == 200
    assert none.json()["results"] == []


def test_recall_endpoint_max_age_days_validation(client):
    resp = client.get("/api/memory/recall?q=olx&max_age_days=oops")
    assert resp.status_code == 400
    assert "max_age_days" in resp.json()["error"]
    resp = client.get("/api/memory/recall?q=olx&max_age_days=-3")
    assert resp.status_code == 400
    assert "max_age_days" in resp.json()["error"]


def test_recall_endpoint_compressed_mode_also_filters(client):
    base = client.get("/api/memory/recall?q=olx&mode=compressed&top_k=8")
    assert base.status_code == 200
    base_results = base.json()["results"]
    assert base_results
    filtered = client.get("/api/memory/recall?q=olx&mode=compressed&top_k=8&max_age_days=30")
    assert filtered.status_code == 200
    assert len(filtered.json()["results"]) == len(base_results)
    assert client.get("/api/memory/recall?q=olx&mode=compressed&top_k=8&max_age_days=0").json()["results"] == []


def test_memory_page_has_max_age_input(client):
    resp = client.get("/memory")
    assert resp.status_code == 200
    assert 'id="search-max-age"' in resp.text
    assert "max_age_days" in resp.text
