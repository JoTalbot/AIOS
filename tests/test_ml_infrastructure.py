"""Tests for ML infrastructure — AutoML, experiment tracking, feature flags."""

from aios_core.automl import AutoML
from aios_core.experiment_tracking import ExperimentTracker
from aios_core.feature_flags import FeatureFlags


def test_automl_stats():
    aml = AutoML()
    s = aml.stats()
    assert isinstance(s, dict)


def test_experiment_tracker_stats():
    et = ExperimentTracker()
    s = et.stats()
    assert isinstance(s, dict)


def test_feature_flags_stats():
    ff = FeatureFlags()
    s = ff.stats()
    assert isinstance(s, dict)
