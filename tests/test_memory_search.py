"""Tests for AgentMemorySystem keyword search (v11.6.0)."""

from __future__ import annotations

import time

from aios_core.agent_memory_system import AgentMemorySystem, MemoryType

TEN_DAYS_AGO = time.time() - 10 * 86400


def _system() -> AgentMemorySystem:
    system = AgentMemorySystem()
    system.record(
        "olx",
        "login",
        "success",
        memory_type=MemoryType.LONG_TERM,
        context={"proxy": "resi-1", "delay_s": 5},
        confidence=1.0,
    )
    system.record("olx", "collect", "success", memory_type=MemoryType.LONG_TERM, context={"items": 40}, confidence=0.6)
    system.record("rozetka", "collect", "failure", memory_type=MemoryType.EPISODIC, context={"code": 503})
    system.record("prom", "parse", "blocked", memory_type=MemoryType.SHORT_TERM)
    return system


def test_search_ranks_exact_cluster_first():
    system = _system()
    results = system.search("rozetka collect 503")
    assert results[0]["platform"] == "rozetka"
    assert results[0]["score"] == 1.0  # all three tokens hit


def test_search_excludes_zero_hits():
    system = _system()
    results = system.search("blocked parse")
    platforms = {r["platform"] for r in results}
    assert platforms == {"prom"}


def test_search_empty_query_returns_empty():
    system = _system()
    assert system.search("") == []
    assert system.search("   ") == []
    assert system.search("!@#$%") == []  # only punctuation — no tokens


def test_search_case_insensitive():
    system = _system()
    lower = system.search("olx login")
    upper = system.search("OLX LOGIN")
    assert [r["memory_id"] for r in lower] == [r["memory_id"] for r in upper]


def test_search_tie_break_by_strength():
    system = _system()
    # Both olx entries contain token "olx" (equal 0.5 score); the
    # higher-strength entry (confidence 1.0 vs 0.6) wins the tie-break
    results = system.search("olx login")
    assert len(results) >= 1
    strengths = [r["strength"] for r in system.search("olx")]
    assert strengths == sorted(strengths, reverse=True)


def test_search_limit_and_pool_filtering():
    system = _system()
    assert len(system.search("success", limit=1)) == 1
    lt_only = system.search("collect", pools="long_term")
    assert lt_only and all(r["type"] == "long_term" for r in lt_only)
    ep_only = system.search("503", pools="episodic")
    assert ep_only and ep_only[0]["platform"] == "rozetka"


def test_search_archive_pool_on_demand():
    system = _system()
    dead = system.record(
        "dead", "collect", "success", memory_type=MemoryType.LONG_TERM, decay_rate=0.9, context={"token_mark": "zzz"}
    )
    dead.created_at = TEN_DAYS_AGO
    system.archive_dead()
    # Active pools no longer contain it
    assert all(r["platform"] != "dead" for r in system.search("zzz"))
    # ...but the archive pool is searchable
    from_archive = system.search("zzz", pools="archive")
    assert from_archive and from_archive[0]["memory_id"] == dead.memory_id
