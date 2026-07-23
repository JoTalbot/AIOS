"""Anomaly detection full."""
from aios_core.anomaly_detection import AnomalyDetector
def test_ad(): s=AnomalyDetector().stats(); assert isinstance(s,dict)
