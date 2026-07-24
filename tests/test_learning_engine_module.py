"""Comprehensive tests for aios_core/learning_engine.py"""

from __future__ import annotations

import pytest

from aios_core.learning_engine import LearningEngine
from aios_core.storage import Database


@pytest.fixture()
def db(tmp_path):
    db = Database(db_path=str(tmp_path / "test.db"))
    yield db
    db.close()


@pytest.fixture()
def engine(db):
    return LearningEngine(db=db)


# ── Recording ──────────────────────────────────────────────────


class TestRecording:
    def test_record(self, engine):
        result = engine.record(experience={"action": "deploy", "outcome": "success"})
        assert isinstance(result, dict)

    def test_record_with_tags(self, engine):
        result = engine.record(
            experience={"action": "test", "outcome": "pass"},
            tags=["ci", "automated"],
        )
        assert isinstance(result, dict)

    def test_record_multiple(self, engine):
        for i in range(5):
            engine.record(experience={"action": f"task_{i}", "outcome": "ok"})
        h = engine.history()
        assert len(h) >= 5


# ── Learning ───────────────────────────────────────────────────


class TestLearning:
    def test_learn(self, engine):
        result = engine.learn(experience={"action": "deploy", "outcome": "success", "duration": 42})
        assert isinstance(result, dict)

    def test_record_task_completion(self, engine):
        # Create a mock task-like object
        class FakeTask:
            name = "deploy"
            task_id = "t1"
            status = "completed"
            steps = []
            metadata = {}

        result = engine.record_task_completion(FakeTask())
        assert isinstance(result, dict)


# ── Pattern extraction ─────────────────────────────────────────


class TestPatterns:
    def test_extract_patterns_empty(self, engine):
        result = engine.extract_patterns()
        assert isinstance(result, list)

    def test_extract_patterns_with_data(self, engine):
        for i in range(10):
            engine.record(experience={"action": "deploy", "outcome": "success" if i < 8 else "fail"})
        patterns = engine.extract_patterns(limit=5)
        assert isinstance(patterns, list)

    def test_analyze_temporal_patterns(self, engine):
        result = engine.analyze_temporal_patterns(hours=24)
        assert isinstance(result, list)

    def test_detect_correlations(self, engine):
        result = engine.detect_correlations()
        assert isinstance(result, list)


# ── Prediction ─────────────────────────────────────────────────


class TestPrediction:
    def test_predict_success(self, engine):
        result = engine.predict_success(task_name="deploy")
        assert isinstance(result, dict)
        assert "confidence" in result or "probability" in result or "score" in result

    def test_predict_with_params(self, engine):
        result = engine.predict_success(
            task_name="deploy",
            params={"env": "production", "version": "2.0"},
        )
        assert isinstance(result, dict)


# ── Recommendations ────────────────────────────────────────────


class TestRecommendations:
    def test_get_recommendations(self, engine):
        result = engine.get_recommendations()
        assert isinstance(result, list)

    def test_get_recommendations_with_context(self, engine):
        result = engine.get_recommendations(context={"task": "deploy", "env": "prod"})
        assert isinstance(result, list)

    def test_generate_evolution_suggestions(self, engine):
        result = engine.generate_evolution_suggestions()
        assert isinstance(result, list)


# ── History and stats ──────────────────────────────────────────


class TestHistoryAndStats:
    def test_history_empty(self, engine):
        assert isinstance(engine.history(), list)

    def test_history_with_limit(self, engine):
        for i in range(20):
            engine.record(experience={"action": f"t{i}"})
        h = engine.history(limit=5)
        assert isinstance(h, list)
        assert len(h) <= 5

    def test_stats(self, engine):
        s = engine.stats()
        assert isinstance(s, dict)

    def test_stats_with_data(self, engine):
        engine.record(experience={"action": "test"})
        engine.learn(experience={"action": "learn"})
        s = engine.stats()
        assert isinstance(s, dict)
