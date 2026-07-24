"""Comprehensive tests for aios_core/reasoning_engine.py"""

from __future__ import annotations

import pytest

from aios_core.reasoning_engine import ReasoningEngine
from aios_core.storage import Database


@pytest.fixture()
def db(tmp_path):
    db = Database(db_path=str(tmp_path / "test.db"))
    yield db
    db.close()


@pytest.fixture()
def engine(db):
    return ReasoningEngine(db=db)


# ── Chain building ─────────────────────────────────────────────


class TestChainBuilding:
    def test_build_chain(self, engine):
        result = engine.build_chain(question="Why is the sky blue?")
        assert isinstance(result, dict)
        assert "chain" in result or "steps" in result or "question" in result

    def test_build_chain_with_context(self, engine):
        result = engine.build_chain(
            question="Is this safe?",
            context={"action": "deploy", "risk": "low"},
        )
        assert isinstance(result, dict)


# ── Reasoning ──────────────────────────────────────────────────


class TestReasoning:
    def test_reason(self, engine):
        result = engine.reason(
            decision="approve",
            rules=["must be safe", "must be tested"],
            sources=["unit tests", "security scan"],
        )
        assert isinstance(result, dict)

    def test_reason_empty_rules(self, engine):
        result = engine.reason(decision="reject", rules=[], sources=[])
        assert isinstance(result, dict)


# ── Forward chaining ───────────────────────────────────────────


class TestForwardChaining:
    def test_forward_chain(self, engine):
        facts = [
            {"fact": "A implies B", "source": "rule1", "confidence": 0.9},
            {"fact": "B implies C", "source": "rule2", "confidence": 0.8},
        ]
        result = engine.forward_chain(facts)
        assert isinstance(result, dict)

    def test_forward_chain_empty(self, engine):
        result = engine.forward_chain([])
        assert isinstance(result, dict)

    def test_forward_chain_max_depth(self, engine):
        facts = [{"fact": "X leads_to Y", "source": "rule3", "confidence": 0.7}]
        result = engine.forward_chain(facts, max_depth=3)
        assert isinstance(result, dict)


# ── Explanation ────────────────────────────────────────────────


class TestExplanation:
    def test_explain(self, engine):
        result = engine.explain(question="What happened?")
        assert isinstance(result, dict)

    def test_explain_with_context(self, engine):
        result = engine.explain(
            question="Why did it fail?",
            context={"error": "timeout", "retry_count": 3},
        )
        assert isinstance(result, dict)


# ── Hypothesis evaluation ─────────────────────────────────────


class TestHypothesis:
    def test_evaluate_hypothesis(self, engine):
        result = engine.evaluate_hypothesis(
            hypothesis="The system is safe",
            evidence=[{"source": "test", "strength": 0.9, "supports": True}],
        )
        assert isinstance(result, dict)

    def test_evaluate_hypothesis_no_evidence(self, engine):
        result = engine.evaluate_hypothesis(hypothesis="X is true")
        assert isinstance(result, dict)


# ── Traces and stats ───────────────────────────────────────────


class TestTracesAndStats:
    def test_traces_empty(self, engine):
        t = engine.traces
        assert isinstance(t, list)

    def test_last_trace(self, engine):
        result = engine.last_trace()
        assert result is None or isinstance(result, dict)

    def test_stats(self, engine):
        s = engine.stats()
        assert isinstance(s, dict)

    def test_stats_after_reasoning(self, engine):
        engine.reason(decision="ok", rules=["r1"], sources=["s1"])
        s = engine.stats()
        assert isinstance(s, dict)
