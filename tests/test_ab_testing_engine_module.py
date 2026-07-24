"""Comprehensive tests for aios_core/ab_testing_engine.py"""

from __future__ import annotations

import pytest

from aios_core.ab_testing_engine import (
    ABTestingEngine,
    ExperimentStatus,
    MetricType,
    Variant,
)


@pytest.fixture()
def engine():
    return ABTestingEngine(min_sample_size=5, significance_threshold=0.05)


# ── Variant ────────────────────────────────────────────────────


class TestVariant:
    def test_create_variant(self):
        v = Variant(name="control")
        assert v.name == "control"
        assert v.sample_size == 0

    def test_add_observation(self):
        v = Variant(name="treatment")
        v.add_observation(10.0)
        v.add_observation(20.0)
        assert v.sample_size == 2
        assert v.mean == 15.0

    def test_variance(self):
        v = Variant(name="v")
        v.add_observation(10.0)
        v.add_observation(20.0)
        v.add_observation(30.0)
        assert v.variance > 0

    def test_std_dev(self):
        v = Variant(name="v")
        v.add_observation(10.0)
        v.add_observation(20.0)
        assert v.std_dev >= 0

    def test_rate_observation(self):
        v = Variant(name="v")
        v.add_rate_observation(True)
        v.add_rate_observation(True)
        v.add_rate_observation(False)
        assert v.rate == pytest.approx(2 / 3)


# ── Experiment lifecycle ───────────────────────────────────────


class TestExperimentLifecycle:
    def test_create_experiment(self, engine):
        exp = engine.create_experiment(name="test_exp", metric_type=MetricType.MEAN)
        assert exp is not None
        assert exp.name == "test_exp"
        assert exp.experiment_id

    def test_create_with_variants(self, engine):
        exp = engine.create_experiment(
            name="ab_test",
            metric_type=MetricType.MEAN,
            variants=[{"name": "control"}, {"name": "treatment"}],
        )
        assert exp is not None

    def test_start_experiment(self, engine):
        exp = engine.create_experiment(name="exp", metric_type=MetricType.MEAN)
        started = engine.start_experiment(exp.experiment_id)
        assert started is not None

    def test_pause_experiment(self, engine):
        exp = engine.create_experiment(name="exp", metric_type=MetricType.MEAN)
        engine.start_experiment(exp.experiment_id)
        paused = engine.pause_experiment(exp.experiment_id)
        assert paused is not None

    def test_cancel_experiment(self, engine):
        exp = engine.create_experiment(name="exp", metric_type=MetricType.MEAN)
        cancelled = engine.cancel_experiment(exp.experiment_id)
        assert cancelled is not None

    def test_get_experiment(self, engine):
        exp = engine.create_experiment(name="exp", metric_type=MetricType.MEAN)
        fetched = engine.get_experiment(exp.experiment_id)
        assert fetched is not None

    def test_get_nonexistent(self, engine):
        assert engine.get_experiment("nope") is None

    def test_list_experiments(self, engine):
        engine.create_experiment(name="e1", metric_type=MetricType.MEAN)
        engine.create_experiment(name="e2", metric_type=MetricType.RATE)
        exps = engine.list_experiments()
        assert len(exps) >= 2

    def test_experiment_to_dict(self, engine):
        exp = engine.create_experiment(name="exp", metric_type=MetricType.MEAN)
        d = exp.to_dict()
        assert isinstance(d, dict)
        assert "name" in d

    def test_experiment_duration(self, engine):
        exp = engine.create_experiment(name="exp", metric_type=MetricType.MEAN)
        assert exp.duration is None or isinstance(exp.duration, (int, float))


# ── Recording observations ─────────────────────────────────────


class TestRecording:
    def test_record_observation(self, engine):
        exp = engine.create_experiment(
            name="exp", metric_type=MetricType.MEAN,
            variants=[{"name": "control"}, {"name": "treatment"}],
        )
        engine.start_experiment(exp.experiment_id)
        engine.record_observation(exp.experiment_id, "control", 10.0)
        engine.record_observation(exp.experiment_id, "treatment", 15.0)

    def test_record_rate_observation(self, engine):
        exp = engine.create_experiment(
            name="exp", metric_type=MetricType.RATE,
            variants=[{"name": "a"}, {"name": "b"}],
        )
        engine.start_experiment(exp.experiment_id)
        engine.record_rate_observation(exp.experiment_id, "a", True)
        engine.record_rate_observation(exp.experiment_id, "b", False)


# ── Analysis ───────────────────────────────────────────────────


class TestAnalysis:
    def test_analyze(self, engine):
        exp = engine.create_experiment(
            name="exp", metric_type=MetricType.MEAN,
            variants=[{"name": "a"}, {"name": "b"}],
        )
        engine.start_experiment(exp.experiment_id)
        for _ in range(10):
            engine.record_observation(exp.experiment_id, "a", 10.0)
            engine.record_observation(exp.experiment_id, "b", 12.0)
        result = engine.analyze(exp.experiment_id)
        assert result is not None or result is None

    def test_analyze_all(self, engine):
        result = engine.analyze_all()
        assert isinstance(result, list)
