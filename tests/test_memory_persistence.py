"""Tests for AgentMemorySystem snapshot persistence (v11.6.0)."""

from __future__ import annotations

import json
import time

import pytest

from aios_core.agent_memory_system import AgentMemorySystem, MemoryType

TEN_DAYS_AGO = time.time() - 10 * 86400


def _populated() -> AgentMemorySystem:
    system = AgentMemorySystem()
    system.record("olx", "login", "success", memory_type=MemoryType.SHORT_TERM, context={"proxy": "a"}, confidence=0.8)
    system.record(
        "rozetka", "collect", "success", memory_type=MemoryType.LONG_TERM, context={"items": 42}, decay_rate=0.005
    )
    for i in range(4):
        system.record(
            "olx",
            "collect",
            "success",
            memory_type=MemoryType.EPISODIC,
            context={"items": 30 + i, "latency_ms": 900 + i * 50, "params": {"pages": 2}},
        )
    system.extract_patterns()
    aged = system.record("prom", "parse", "failure", memory_type=MemoryType.LONG_TERM, decay_rate=0.9)
    aged.created_at = TEN_DAYS_AGO
    system.archive_dead()
    system.optimize_storage()
    system.deduplicate()
    return system


def test_snapshot_round_trip_counts():
    source = _populated()
    target = AgentMemorySystem()
    report = target.restore(source.snapshot())
    assert report["short_term"] == 1
    assert report["long_term"] == 1  # rozetka entry; prom entry archived
    assert report["episodic"] == 4
    assert report["archive"] == 1
    assert report["patterns"] >= 1
    assert target.stats()["dedup"]["removed_total"] == source._dedup_removed_total


def test_snapshot_preserves_decay_relevant_fields():
    source = _populated()
    target = AgentMemorySystem()
    target.restore(source.snapshot())
    original = source._long_term[0]
    restored = target._long_term[0]
    assert restored.memory_id == original.memory_id
    assert restored.confidence == original.confidence
    assert restored.decay_rate == original.decay_rate
    assert restored.created_at == original.created_at
    assert restored.last_accessed == original.last_accessed
    assert restored.access_count == original.access_count
    assert restored.priority == original.priority
    assert restored.metadata == original.metadata
    assert restored.strength == pytest.approx(original.strength)


def test_id_counter_never_collides_after_restore():
    source = _populated()
    existing = {
        e.memory_id for p in (source._short_term, source._long_term, source._episodic, source._archive) for e in p
    }
    target = AgentMemorySystem()
    target.restore(source.snapshot())
    new_entry = target.record("new", "action", "ok")
    assert new_entry.memory_id not in existing
    # counter semantics: mem_N with N greater than every existing N
    assert int(new_entry.memory_id.split("_")[1]) > max(
        int(mid.split("_")[1]) for mid in existing if mid.startswith("mem_")
    )


def test_save_and_load_file_round_trip(tmp_path):
    source = _populated()
    target_path = tmp_path / "nested" / "memory.json"
    result = source.save(str(target_path))
    assert result["saved"] == str(target_path)
    assert target_path.exists()
    # Atomic write: no leftover tmp file
    assert not target_path.with_suffix(".json.tmp").exists()
    # File is valid JSON with the expected top-level shape
    data = json.loads(target_path.read_text(encoding="utf-8"))
    assert data["format"] == AgentMemorySystem.SNAPSHOT_FORMAT
    assert set(data["pools"]) == {"short_term", "long_term", "episodic", "archive"}

    target = AgentMemorySystem()
    report = target.load(str(target_path))
    assert report["loaded"] == str(target_path)
    assert report["episodic"] == 4
    assert report["archive"] == 1


def test_load_replaces_state_entirely(tmp_path):
    source = _populated()
    target_path = tmp_path / "memory.json"
    source.save(str(target_path))

    target = AgentMemorySystem()
    target.record("junk", "junk", "junk", memory_type=MemoryType.LONG_TERM)
    target.record("junk", "junk", "junk", memory_type=MemoryType.EPISODIC)
    target.load(str(target_path))
    platforms = {e.platform for e in [*target._long_term, *target._episodic]}
    assert "junk" not in platforms


def test_restore_rejects_bad_format():
    target = AgentMemorySystem()
    with pytest.raises(ValueError, match="format"):
        target.restore({"format": 999, "pools": {}})
    with pytest.raises(ValueError, match="pools"):
        target.restore({"format": 1})
    with pytest.raises(ValueError, match="pools"):
        target.restore({"format": 1, "pools": {"short_term": []}})


def test_patterns_round_trip():
    source = _populated()
    assert source._patterns  # seeded 4 episodic successes produce a pattern
    target = AgentMemorySystem()
    target.restore(source.snapshot())
    assert len(target._patterns) == len(source._patterns)
    same = next(iter(target._patterns.values()))
    assert same.platform == "olx"
    assert same.action == "collect"
    assert same.sample_size >= 3
    assert hasattr(same, "discovered_at")


def test_compressed_index_is_derived_not_persisted(tmp_path):
    source = _populated()
    assert source._compressed  # index built pre-save
    target_path = tmp_path / "memory.json"
    data = json.loads(json.dumps(source.snapshot()))
    assert "compressed" not in json.dumps(data["pools"])

    source.save(str(target_path))
    target = AgentMemorySystem()
    target.load(str(target_path))
    assert target._compressed == {}  # derived state starts empty
    assert target.compression_stats() == {}
    # Rebuilding works on restored data
    report = target.optimize_storage()
    assert report["entries_compressed"] == report["entries_compressed"] >= 5


def test_archive_report_cleared_on_restore():
    source = _populated()
    assert source.archive_stats()["last_report"]["archived"] == 1
    target = AgentMemorySystem()
    target.restore(source.snapshot())
    # The archive POOL survives; derived run reports do not
    assert target.archive_stats()["archived_total"] == 1
    assert target.archive_stats()["last_report"] == {}
