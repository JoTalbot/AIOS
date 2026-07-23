"""Tests for ML, predictive autonomy and anomaly detection."""

from aios_core.predictive_autonomy import PredictiveAutonomyRegulator
from aios_core.anomaly_detection import AnomalyDetector
from aios_core.explainable_ai import ExplainableAI


def test_predictive_autonomy_stats():
    pa = PredictiveAutonomyRegulator()
    s = pa.stats()
    assert isinstance(s, dict)


def test_anomaly_detector_stats():
    ad = AnomalyDetector()
    s = ad.stats()
    assert isinstance(s, dict)


def test_explainable_ai_stats():
    ea = ExplainableAI()
    s = ea.stats()
    assert isinstance(s, dict)
