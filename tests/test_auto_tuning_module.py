"""Tests for aios_core/auto_tuning.py"""
from __future__ import annotations
import pytest
from aios_core.auto_tuning import AutoTuningEngine, TunableParam


class TestTunableParam:
    def test_create(self):
        p = TunableParam(name="lr", param_type="float", min_value=0.001, max_value=1.0)
        assert p.name == "lr"

    def test_random_value(self):
        p = TunableParam(name="x", param_type="float", min_value=0.0, max_value=1.0)
        v = p.random_value()
        assert 0.0 <= v <= 1.0

    def test_grid_values(self):
        p = TunableParam(name="x", param_type="float", min_value=0.0, max_value=1.0)
        vals = p.grid_values()
        assert isinstance(vals, list)

    def test_clamp(self):
        p = TunableParam(name="x", param_type="float", min_value=0.0, max_value=1.0)
        assert p.clamp(1.5) == 1.0
        assert p.clamp(0.5) == 0.5


class TestAutoTuningEngine:
    def test_create(self):
        engine = AutoTuningEngine(scoring_fn=lambda p: 1.0)
        assert engine is not None

    def test_register_param(self):
        engine = AutoTuningEngine(scoring_fn=lambda p: 1.0)
        engine.register_param(TunableParam(name="lr", param_type="float", min_value=0.001, max_value=1.0))

    def test_register_params(self):
        engine = AutoTuningEngine(scoring_fn=lambda p: 1.0)
        engine.register_params([
            TunableParam(name="lr", param_type="float", min_value=0.001, max_value=1.0),
            TunableParam(name="batch", param_type="int", min_value=8, max_value=128),
        ])

    def test_get_current_params(self):
        engine = AutoTuningEngine(scoring_fn=lambda p: 1.0)
        engine.register_param(TunableParam(name="x", param_type="float", min_value=0.0, max_value=1.0))
        params = engine.get_current_params()
        assert isinstance(params, dict)

    def test_get_default_params(self):
        engine = AutoTuningEngine(scoring_fn=lambda p: 1.0)
        engine.register_param(TunableParam(name="x", param_type="float", min_value=0.0, max_value=1.0, default=0.5))
        defaults = engine.get_default_params()
        assert isinstance(defaults, dict)

    def test_tune(self):
        engine = AutoTuningEngine(scoring_fn=lambda p: -(p.get("x", 0) - 0.5) ** 2)
        engine.register_param(TunableParam(name="x", param_type="float", min_value=0.0, max_value=1.0))
        result = engine.tune(max_iterations=5)
        assert result is not None

    def test_get_best_params(self):
        engine = AutoTuningEngine(scoring_fn=lambda p: 1.0)
        engine.register_param(TunableParam(name="x", param_type="float", min_value=0.0, max_value=1.0))
        best = engine.get_best_params()
        assert isinstance(best, dict)

    def test_stats(self):
        engine = AutoTuningEngine(scoring_fn=lambda p: 1.0)
        s = engine.stats()
        assert isinstance(s, dict)
