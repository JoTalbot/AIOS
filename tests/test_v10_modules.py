"""Tests for ab_testing_engine module — A/B experiment comparison and statistical significance."""

from __future__ import annotations

from aios_core.ab_testing_engine import (
    ABTestingEngine,
    Experiment,
    ExperimentStatus,
    MetricType,
    Variant,
)


class TestVariant:
    """Tests for Variant dataclass."""

    def test_sample_size_observations(self) -> None:
        """Sample size from observations."""
        v = Variant(name="a", observations=[1.0, 2.0, 3.0])
        assert v.sample_size == 3

    def test_sample_size_rate(self) -> None:
        """Sample size from rate metrics."""
        v = Variant(name="a", rate_successes=80, rate_total=100)
        assert v.sample_size == 100

    def test_mean(self) -> None:
        """Mean calculation."""
        v = Variant(name="a", observations=[100, 200, 300])
        assert v.mean == 200.0

    def test_variance(self) -> None:
        """Variance calculation."""
        v = Variant(name="a", observations=[10, 20, 30])
        assert abs(v.variance - 100.0) < 1.0

    def test_std_dev(self) -> None:
        """Standard deviation."""
        v = Variant(name="a", observations=[10, 20, 30])
        assert abs(v.std_dev - 10.0) < 1.0

    def test_rate(self) -> None:
        """Rate calculation."""
        v = Variant(name="a", rate_successes=9, rate_total=10)
        assert v.rate == 0.9

    def test_add_observation(self) -> None:
        """Add observation updates mean."""
        v = Variant(name="a")
        v.add_observation(100.0)
        v.add_observation(200.0)
        assert v.mean == 150.0
        assert v.sample_size == 2

    def test_add_rate_observation(self) -> None:
        """Add rate observation."""
        v = Variant(name="a")
        v.add_rate_observation(True)
        v.add_rate_observation(False)
        v.add_rate_observation(True)
        assert v.rate_successes == 2
        assert v.rate_total == 3
        assert v.rate == 2 / 3


class TestExperiment:
    """Tests for Experiment dataclass."""

    def test_duration(self) -> None:
        """Duration computed from timestamps."""
        exp = Experiment(
            experiment_id="e1", name="test", started_at=100.0, completed_at=115.0
        )
        assert exp.duration == 15.0

    def test_duration_running(self) -> None:
        """Duration for running experiment uses current time."""
        import time as _time
        exp = Experiment(experiment_id="e1", name="test", started_at=_time.time() - 10)
        assert exp.duration > 0

    def test_to_dict(self) -> None:
        """Serialize experiment to dict."""
        v = Variant(name="a", observations=[1.0])
        exp = Experiment(experiment_id="e1", name="test", variants=[v])
        d = exp.to_dict()
        assert d["experiment_id"] == "e1"
        assert len(d["variants"]) == 1


class TestABTestingEngine:
    """Tests for ABTestingEngine."""

    def test_create_experiment(self) -> None:
        """Create experiment with variants."""
        engine = ABTestingEngine()
        exp = engine.create_experiment("test_exp", MetricType.MEAN)
        assert exp.experiment_id.startswith("exp_")
        assert len(exp.variants) == 2  # Default A/B pair

    def test_create_experiment_custom_variants(self) -> None:
        """Create experiment with custom variants."""
        engine = ABTestingEngine()
        exp = engine.create_experiment(
            "test_exp",
            variants=[
                {"name": "baseline", "description": "Default"},
                {"name": "optimized", "description": "Optimized strategy"},
            ],
        )
        assert len(exp.variants) == 2
        assert exp.variants[0].name == "baseline"

    def test_create_experiment_single_variant_adds_baseline(self) -> None:
        """One variant → baseline auto-added."""
        engine = ABTestingEngine()
        exp = engine.create_experiment(
            "test_exp", variants=[{"name": "strategy_b"}]
        )
        assert len(exp.variants) == 2
        assert exp.variants[0].name == "baseline"

    def test_start_experiment(self) -> None:
        """Start draft experiment."""
        engine = ABTestingEngine()
        exp = engine.create_experiment("test")
        result = engine.start_experiment(exp.experiment_id)
        assert result.status == ExperimentStatus.RUNNING

    def test_record_observation(self) -> None:
        """Record metric observations."""
        engine = ABTestingEngine()
        exp = engine.create_experiment("test", MetricType.MEAN)
        engine.start_experiment(exp.experiment_id)

        engine.record_observation(exp.experiment_id, "variant_a", 100.0)
        engine.record_observation(exp.experiment_id, "variant_b", 200.0)

        v_a = exp.variants[0]
        assert v_a.mean == 100.0
        assert v_a.sample_size == 1

    def test_record_rate_observation(self) -> None:
        """Record rate observations."""
        engine = ABTestingEngine()
        exp = engine.create_experiment("test", MetricType.RATE)
        engine.start_experiment(exp.experiment_id)

        engine.record_rate_observation(exp.experiment_id, "variant_a", True)
        engine.record_rate_observation(exp.experiment_id, "variant_a", False)
        engine.record_rate_observation(exp.experiment_id, "variant_b", True)

        assert exp.variants[0].rate_successes == 1
        assert exp.variants[0].rate_total == 2

    def test_analyze_insufficient_data(self) -> None:
        """Analyze with insufficient data → no significance."""
        engine = ABTestingEngine(min_sample_size=30)
        exp = engine.create_experiment("test", MetricType.MEAN)
        engine.start_experiment(exp.experiment_id)

        for i in range(5):
            engine.record_observation(exp.experiment_id, "variant_a", 100.0 + i)
            engine.record_observation(exp.experiment_id, "variant_b", 200.0 + i)

        result = engine.analyze(exp.experiment_id)
        assert result is not None
        assert not result.is_significant
        assert result.recommendation == "Insufficient sample size — continue experiment"

    def test_analyze_mean_significant(self) -> None:
        """Analyze mean metrics with significant difference."""
        engine = ABTestingEngine(min_sample_size=30, significance_threshold=0.05)
        exp = engine.create_experiment("test", MetricType.MEAN)
        engine.start_experiment(exp.experiment_id)

        # variant_a: low values, variant_b: high values (clear difference)
        for i in range(50):
            engine.record_observation(exp.experiment_id, "variant_a", 100.0 + random.uniform(-5, 5))
            engine.record_observation(exp.experiment_id, "variant_b", 300.0 + random.uniform(-5, 5))

        result = engine.analyze(exp.experiment_id)
        assert result is not None
        assert result.is_significant
        assert result.winner == "variant_b"
        assert result.p_value < 0.05

    def test_analyze_rate_significant(self) -> None:
        """Analyze rate metrics with significant difference."""
        engine = ABTestingEngine(min_sample_size=30, significance_threshold=0.05)
        exp = engine.create_experiment("test", MetricType.RATE)
        engine.start_experiment(exp.experiment_id)

        # variant_a: 50% success rate, variant_b: 90% success rate
        for i in range(100):
            engine.record_rate_observation(exp.experiment_id, "variant_a", i < 50)
            engine.record_rate_observation(exp.experiment_id, "variant_b", i < 90)

        result = engine.analyze(exp.experiment_id)
        assert result is not None
        assert result.is_significant
        assert result.winner == "variant_b"

    def test_pause_and_resume(self) -> None:
        """Pause and resume experiment."""
        engine = ABTestingEngine()
        exp = engine.create_experiment("test")
        engine.start_experiment(exp.experiment_id)
        engine.pause_experiment(exp.experiment_id)
        assert exp.status == ExperimentStatus.PAUSED

    def test_cancel_experiment(self) -> None:
        """Cancel experiment."""
        engine = ABTestingEngine()
        exp = engine.create_experiment("test")
        engine.start_experiment(exp.experiment_id)
        result = engine.cancel_experiment(exp.experiment_id)
        assert result.status == ExperimentStatus.CANCELLED

    def test_analyze_all(self) -> None:
        """Analyze all running experiments."""
        engine = ABTestingEngine(min_sample_size=5)
        exp1 = engine.create_experiment("exp1", MetricType.MEAN)
        engine.start_experiment(exp1.experiment_id)
        for i in range(10):
            engine.record_observation(exp1.experiment_id, "variant_a", 100 + i)
            engine.record_observation(exp1.experiment_id, "variant_b", 200 + i)

        results = engine.analyze_all()
        assert len(results) >= 1

    def test_auto_complete(self) -> None:
        """Auto-complete experiment when significance reached."""
        engine = ABTestingEngine(min_sample_size=5, significance_threshold=0.05)
        exp = engine.create_experiment("test", MetricType.RATE)
        engine.start_experiment(exp.experiment_id)

        for i in range(100):
            engine.record_rate_observation(exp.experiment_id, "variant_a", i < 30)
            engine.record_rate_observation(exp.experiment_id, "variant_b", i < 80)

        result = engine.auto_complete(exp.experiment_id)
        assert result is not None
        assert result.status == ExperimentStatus.COMPLETED

    def test_list_experiments(self) -> None:
        """List and filter experiments."""
        engine = ABTestingEngine()
        exp1 = engine.create_experiment("exp1")
        exp2 = engine.create_experiment("exp2")
        engine.start_experiment(exp1.experiment_id)

        all_exps = engine.list_experiments()
        assert len(all_exps) == 2

        running = engine.list_experiments(ExperimentStatus.RUNNING)
        assert len(running) == 1

    def test_chi_square_test(self) -> None:
        """Chi-square test for rate comparison."""
        engine = ABTestingEngine()
        a = Variant(name="a", rate_successes=80, rate_total=100)
        b = Variant(name="b", rate_successes=50, rate_total=100)
        chi2, p = engine._chi_square_test(a, b)
        assert chi2 > 0
        assert p < 0.05  # Significant difference

    def test_t_test(self) -> None:
        """T-test for mean comparison with variance."""
        engine = ABTestingEngine()
        # Use different means with some natural variance
        a = Variant(name="a", observations=[100 + i * 0.5 for i in range(50)])
        b = Variant(name="b", observations=[200 + i * 0.5 for i in range(50)])
        t_stat, p = engine._t_test(a, b)
        assert abs(t_stat) > 5  # Significant
        assert p < 0.01

    def test_normal_cdf(self) -> None:
        """Normal CDF approximation."""
        engine = ABTestingEngine()
        # CDF(0) ≈ 0.5
        assert abs(engine._normal_cdf(0) - 0.5) < 0.01
        # CDF(1.96) ≈ 0.975
        assert abs(engine._normal_cdf(1.96) - 0.975) < 0.01
        # CDF(-1.96) ≈ 0.025
        assert abs(engine._normal_cdf(-1.96) - 0.025) < 0.01

import random


class TestKnowledgeGraphUnit:
    """Unit tests for KnowledgeGraph (new module)."""

    def test_add_triple(self) -> None:
        """Add triple to graph."""
        from aios_core.knowledge_graph import KnowledgeGraph, Triple
        kg = KnowledgeGraph()
        kg.add_triple(Triple(subject="iphone", predicate="sold_by", object="seller1"))
        assert kg.count_nodes() == 2  # iphone + seller1

    def test_add_relation(self) -> None:
        """Add relation via API-compatible method."""
        from aios_core.knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph()
        result = kg.add_relation(source_id="iphone", target_id="seller1", relation="sold_by")
        assert result["source"] == "iphone"
        assert result["target"] == "seller1"

    def test_find_path(self) -> None:
        """Find path between entities."""
        from aios_core.knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_relation(source_id="A", target_id="B", relation="r")
        kg.add_relation(source_id="B", target_id="C", relation="r")
        path_result = kg.path("A", "C")
        assert len(path_result) == 2  # Two edges: A→B, B→C

    def test_infer(self) -> None:
        """Inference rules derive new relationships."""
        from aios_core.knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_relation(source_id="iphone", target_id="seller1", relation="sold_by")
        kg.add_relation(source_id="seller1", target_id="Kyiv", relation="located_in")
        inferred = kg.infer()
        assert inferred > 0
        # Should infer iphone → located_in → Kyiv

    def test_stats(self) -> None:
        """Graph statistics."""
        from aios_core.knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_relation(source_id="A", target_id="B", relation="r")
        stats = kg.stats()
        assert stats["entities"] >= 2
        assert stats["edges"] >= 1


class TestAutoTuningEngine:
    """Tests for AutoTuningEngine."""

    def test_register_params(self) -> None:
        """Register tunable parameters."""
        from aios_core.auto_tuning import AutoTuningEngine, ParamType, TunableParam
        engine = AutoTuningEngine()
        engine.register_params([
            TunableParam(name="timeout", param_type=ParamType.FLOAT, min_value=1.0, max_value=30.0, default=10.0),
            TunableParam(name="max_items", param_type=ParamType.INT, min_value=10, max_value=500, default=100),
        ])
        assert len(engine._params) == 2
        assert engine.get_default_params()["timeout"] == 10.0

    def test_record_feedback(self) -> None:
        """Record performance feedback."""
        from aios_core.auto_tuning import (
            AutoTuningEngine,
            ParamType,
            PerformanceFeedback,
            TunableParam,
        )
        engine = AutoTuningEngine()
        engine.register_param(TunableParam(name="timeout", param_type=ParamType.FLOAT, min_value=1.0, max_value=30.0, default=10.0))

        fb = PerformanceFeedback(
            params={"timeout": 10.0},
            success_rate=0.8,
            latency_ms=500,
            items_collected=50,
            errors=2,
        )
        engine.record_feedback(fb)
        assert engine._best_score > 0.0

    def test_tune_grid(self) -> None:
        """Grid search tuning."""
        from aios_core.auto_tuning import AutoTuningEngine, ParamType, TunableParam
        engine = AutoTuningEngine()

        # Custom scoring: prefer timeout around 5
        def scoring(config):
            return max(0, 1 - abs(config.get("timeout", 10) - 5) / 30)

        engine.register_param(
            TunableParam(name="timeout", param_type=ParamType.FLOAT, min_value=1.0, max_value=30.0, step=1.0, default=10.0)
        )
        result = engine.tune_grid(scoring_fn=scoring)
        assert result.strategy.value == "grid_search"
        assert result.score > 0

    def test_tune_random(self) -> None:
        """Random search tuning."""
        from aios_core.auto_tuning import AutoTuningEngine, ParamType, TunableParam
        engine = AutoTuningEngine()

        def scoring(config):
            return 0.5 + config.get("max_items", 100) / 1000

        engine.register_params([
            TunableParam(name="max_items", param_type=ParamType.INT, min_value=10, max_value=500, default=100),
        ])
        result = engine.tune_random(n_iterations=20, scoring_fn=scoring)
        assert result.iterations == 20

    def test_tune_hill_climbing(self) -> None:
        """Hill climbing optimization."""
        from aios_core.auto_tuning import AutoTuningEngine, ParamType, TunableParam
        engine = AutoTuningEngine()

        def scoring(config):
            # Optimum around timeout=5
            return max(0, 1 - abs(config.get("timeout", 10) - 5) / 30)

        engine.register_param(
            TunableParam(name="timeout", param_type=ParamType.FLOAT, min_value=1.0, max_value=30.0, default=10.0)
        )
        # Seed with feedback at default
        from aios_core.auto_tuning import PerformanceFeedback
        engine.record_feedback(PerformanceFeedback(
            params={"timeout": 10.0}, success_rate=0.5, latency_ms=1000, items_collected=50, errors=0
        ))
        result = engine.tune_hill_climbing(n_iterations=30, scoring_fn=scoring)
        assert result.score >= engine._default_score

    def test_stats(self) -> None:
        """Tuning engine stats."""
        from aios_core.auto_tuning import (
            AutoTuningEngine,
            ParamType,
            PerformanceFeedback,
            TunableParam,
        )
        engine = AutoTuningEngine()
        engine.register_param(TunableParam(name="timeout", param_type=ParamType.FLOAT, min_value=1.0, max_value=30.0, default=10.0))
        engine.record_feedback(PerformanceFeedback(
            params={"timeout": 10.0}, success_rate=0.7, latency_ms=500, items_collected=50, errors=1
        ))
        stats = engine.stats()
        assert stats["params_count"] == 1
        assert stats["feedback_count"] == 1
        assert stats["best_score"] > 0

    def test_get_best_params(self) -> None:
        """Get best parameters after feedback."""
        from aios_core.auto_tuning import (
            AutoTuningEngine,
            ParamType,
            PerformanceFeedback,
            TunableParam,
        )
        engine = AutoTuningEngine()
        engine.register_param(TunableParam(name="timeout", param_type=ParamType.FLOAT, min_value=1.0, max_value=30.0, default=10.0))

        # First feedback (poor)
        engine.record_feedback(PerformanceFeedback(
            params={"timeout": 10.0}, success_rate=0.3, latency_ms=2000, items_collected=10, errors=5
        ))
        # Second feedback (better)
        engine.record_feedback(PerformanceFeedback(
            params={"timeout": 5.0}, success_rate=0.9, latency_ms=200, items_collected=80, errors=0
        ))
        best = engine.get_best_params()
        assert best["timeout"] == 5.0

    def test_tunable_param_grid_values(self) -> None:
        """Grid values generation."""
        from aios_core.auto_tuning import ParamType, TunableParam
        p = TunableParam(name="test", param_type=ParamType.INT, min_value=0, max_value=10, step=2)
        values = p.grid_values()
        assert values == [0, 2, 4, 6, 8, 10]

    def test_tunable_param_random_value(self) -> None:
        """Random value within range."""
        from aios_core.auto_tuning import ParamType, TunableParam
        p = TunableParam(name="test", param_type=ParamType.INT, min_value=0, max_value=100)
        val = p.random_value()
        assert 0 <= val <= 100

    def test_bool_param_grid(self) -> None:
        """Bool param grid values."""
        from aios_core.auto_tuning import ParamType, TunableParam
        p = TunableParam(name="test", param_type=ParamType.BOOL)
        assert p.grid_values() == [True, False]

    def test_choice_param(self) -> None:
        """Choice parameter."""
        from aios_core.auto_tuning import ParamType, TunableParam
        p = TunableParam(name="strategy", param_type=ParamType.CHOICE, choices=["fast", "slow", "balanced"])
        val = p.random_value()
        assert val in ["fast", "slow", "balanced"]
