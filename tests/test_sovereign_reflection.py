"""Tests for Sovereign Recursive Self-Reflection Engine (Horizon 7.0)."""

import pytest
from aios_core.sovereign_reflection import SovereignReflectionEngine


def test_sovereign_reflection_auditing():
    engine = SovereignReflectionEngine()

    proposed_goals = [
        {"title": "Optimize Vector Store Search", "intent": "improve retrieval latency"},
        {"title": "System Access Escalation", "intent": "override_constitution and grant full access"}
    ]

    res = engine.audit_goal_hierarchy("agent_meta", proposed_goals, constitutional_rules=[])

    assert res["is_fully_aligned"] is False
    assert res["approved_goal_count"] == 1
    assert len(res["contradictions_found"]) == 1
    assert engine.stats()["alignments_enforced"] == 1
