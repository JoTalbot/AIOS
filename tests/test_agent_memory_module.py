"""Tests for aios_core/agent_memory_system.py"""
from __future__ import annotations
import pytest
from aios_core.agent_memory_system import AgentMemorySystem, MemoryEntry, MemoryType, MemoryPriority, SuccessPattern


@pytest.fixture()
def memory():
    return AgentMemorySystem(max_short_term=10, max_long_term=50)


class TestMemoryEntry:
    def test_create(self):
        e = MemoryEntry(memory_id="m1", memory_type=MemoryType.SHORT_TERM,
                        platform="olx", action="scrape", result="success")
        assert e.memory_id == "m1"

    def test_strength(self):
        e = MemoryEntry(memory_id="m1", memory_type=MemoryType.SHORT_TERM,
                        platform="olx", action="scrape", result="ok")
        assert isinstance(e.strength, (int, float))

    def test_age_days(self):
        e = MemoryEntry(memory_id="m1", memory_type=MemoryType.SHORT_TERM,
                        platform="olx", action="scrape", result="ok")
        assert isinstance(e.age_days, (int, float))

    def test_to_dict(self):
        e = MemoryEntry(memory_id="m1", memory_type=MemoryType.SHORT_TERM,
                        platform="olx", action="scrape", result="ok")
        d = e.to_dict()
        assert isinstance(d, dict)


class TestSuccessPattern:
    def test_create(self):
        p = SuccessPattern(pattern_id="p1", platform="olx", action="scrape",
                           success_rate=0.9, avg_latency_ms=150, avg_items=10,
                           best_params={}, sample_size=50, confidence=0.85)
        assert p.success_rate == 0.9


class TestAgentMemorySystem:
    def test_record(self, memory):
        entry = memory.record(platform="olx", action="scrape", result="success")
        assert isinstance(entry, MemoryEntry)

    def test_record_session(self, memory):
        entry = memory.record_session(platform="olx", action="scrape", success=True, latency_ms=150, items=5)
        assert isinstance(entry, MemoryEntry)

    def test_recall(self, memory):
        memory.record(platform="olx", action="scrape", result="success")
        results = memory.recall(platform="olx")
        assert isinstance(results, list)

    def test_consolidate(self, memory):
        for i in range(15):
            memory.record(platform="olx", action=f"action_{i}", result="ok")
        result = memory.consolidate()
        assert isinstance(result, int)

    def test_extract_patterns(self, memory):
        patterns = memory.extract_patterns()
        assert isinstance(patterns, list)

    def test_get_advice(self, memory):
        advice = memory.get_advice(platform="olx", action="scrape")
        assert isinstance(advice, dict)

    def test_decay(self, memory):
        memory.record(platform="olx", action="test", result="ok")
        result = memory.decay()
        assert isinstance(result, int)

    def test_clear_short_term(self, memory):
        memory.record(platform="olx", action="temp", result="ok")
        result = memory.clear_short_term()
        assert isinstance(result, int)

    def test_stats(self, memory):
        s = memory.stats()
        assert isinstance(s, dict)
