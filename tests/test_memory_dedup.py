"""Tests for the Memory Deduplication Engine (v11.4.0)."""

from __future__ import annotations

import pytest

from aios_core.agent_memory_system import AgentMemorySystem, MemoryType
from aios_core.memory_dedup import MemoryDeduplicator


def _system_with(memories: list[tuple], memory_type=MemoryType.LONG_TERM) -> AgentMemorySystem:
    """Build a memory system; each tuple is (platform, action, result, context)."""
    system = AgentMemorySystem()
    for platform, action, result, context in memories:
        system.record(platform, action, result, memory_type=memory_type, context=context)
    return system


def test_deduplicator_threshold_validation():
    with pytest.raises(ValueError):
        MemoryDeduplicator(threshold=0.0)
    with pytest.raises(ValueError):
        MemoryDeduplicator(threshold=1.5)
    # Boundary values are legal
    MemoryDeduplicator(threshold=0.01)
    MemoryDeduplicator(threshold=1.0)


def test_find_duplicates_empty_memory():
    system = AgentMemorySystem()
    assert system.find_duplicates() == []
    report = system.deduplicate()
    assert report["groups_found"] == 0
    assert report["entries_removed"] == 0


def test_find_duplicates_detects_identical_pair():
    system = _system_with(
        [
            ("olx", "login", "success", {"proxy": "a"}),
            ("olx", "login", "success", {"proxy": "a"}),  # identical -> duplicate
            ("rozetka", "collect", "failure", {"code": 503}),  # unrelated
        ]
    )
    groups = system.find_duplicates()
    assert len(groups) == 1
    group = groups[0]
    assert group["size"] == 2
    assert sorted(group["member_ids"]) == ["mem_1", "mem_2"]
    # Identical text -> identical vectors -> cosine ~1.0
    assert group["avg_similarity"] == pytest.approx(1.0, abs=1e-3)


def test_find_duplicates_no_false_positives_on_distinct():
    system = _system_with(
        [
            ("olx", "login", "success", {"proxy": "a", "delay_s": 5}),
            ("rozetka", "collect", "failure", {"code": 503, "page": 12}),
            ("prom", "parse", "blocked", {"captcha": True}),
        ]
    )
    assert system.find_duplicates() == []


def test_find_duplicates_pool_filtering():
    system = AgentMemorySystem()
    for _ in range(2):
        system.record("olx", "login", "success", memory_type=MemoryType.LONG_TERM, context={"proxy": "a"})
        system.record("olx", "login", "success", memory_type=MemoryType.EPISODIC, context={"proxy": "a"})

    lt_groups = system.find_duplicates(pool="long_term")
    assert len(lt_groups) == 1
    ep_groups = system.find_duplicates(pool="episodic")
    assert len(ep_groups) == 1
    # Cross-pool scan merges all four identical texts into ONE group
    all_groups = system.find_duplicates(pool="all")
    assert len(all_groups) == 1
    assert all_groups[0]["size"] == 4


def test_deduplicate_merges_and_shrinks_pools():
    system = _system_with(
        [
            ("olx", "login", "success", {"proxy": "a"}),
            ("olx", "login", "success", {"proxy": "a"}),
            ("olx", "login", "success", {"proxy": "a"}),
            ("rozetka", "collect", "failure", {"code": 503}),
        ]
    )
    report = system.deduplicate()
    assert report["groups_found"] == 1
    assert report["entries_removed"] == 2
    assert len(system._long_term) == 2  # 1 survivor + 1 unrelated
    survivors = {e.memory_id for e in system._long_term}
    assert "mem_4" in survivors  # the unrelated one always survives
    assert len(system._compressed) == 2  # index shrank too


def test_deduplicate_keeps_strongest_and_merges_stats():
    system = _system_with(
        [
            ("olx", "login", "success", {"proxy": "a"}),
            ("olx", "login", "success", {"proxy": "a"}),
        ]
    )
    strong, weak = system._long_term
    strong.confidence = 0.9
    strong.access_count = 7
    weak.confidence = 0.4
    weak.access_count = 3

    report = system.deduplicate()
    assert report["merged"][0]["representative_id"] == strong.memory_id
    survivor = system._long_term[0]
    assert survivor.memory_id == strong.memory_id
    assert survivor.access_count == 10  # 7 + 3 absorbed
    assert survivor.confidence == 0.9  # best confidence kept


def test_deduplicate_is_idempotent():
    system = _system_with(
        [
            ("olx", "login", "success", {"proxy": "a"}),
            ("olx", "login", "success", {"proxy": "a"}),
        ]
    )
    first = system.deduplicate()
    assert first["entries_removed"] == 1
    second = system.deduplicate()
    assert second["groups_found"] == 0
    assert second["entries_removed"] == 0
    assert system._dedup_removed_total == 1  # lifetime counter only counts real removals


def test_short_term_never_deduplicated():
    system = AgentMemorySystem()
    system.record("olx", "click", "success", memory_type=MemoryType.SHORT_TERM, context={"x": 1})
    system.record("olx", "click", "success", memory_type=MemoryType.SHORT_TERM, context={"x": 1})
    report = system.deduplicate()
    assert report["entries_removed"] == 0
    assert len(system._short_term) == 2  # short-term pool untouched


def test_groups_sorted_by_size_desc():
    system = _system_with(
        [
            ("a", "act", "success", {"k": 1}),
            ("a", "act", "success", {"k": 1}),  # pair A
            ("b", "act", "success", {"k": 999}),  # filler between clusters
            ("c", "act", "success", {"k": 5}),
            ("c", "act", "success", {"k": 5}),
            ("c", "act", "success", {"k": 5}),  # triple C
        ]
    )
    groups = system.find_duplicates()
    assert len(groups) == 2
    assert groups[0]["size"] == 3  # largest group first
    assert groups[1]["size"] == 2


def test_stats_exposes_dedup_block():
    system = _system_with(
        [
            ("olx", "login", "success", {"proxy": "a"}),
            ("olx", "login", "success", {"proxy": "a"}),
        ]
    )
    system.deduplicate()
    stats = system.stats()
    assert "dedup" in stats
    assert stats["dedup"]["removed_total"] == 1
    assert stats["dedup"]["last_report"]["groups_found"] == 1


def test_compressed_recall_still_works_after_dedup():
    system = _system_with(
        [
            ("olx", "login", "success", {"proxy": "a"}),
            ("olx", "login", "success", {"proxy": "a"}),
            ("rozetka", "collect", "failure", {"code": 503}),
        ]
    )
    system.optimize_storage()
    system.deduplicate()
    recalled = system.recall_compressed("olx login success", top_k=1)
    assert len(recalled) == 1
    assert recalled[0].platform == "olx"
