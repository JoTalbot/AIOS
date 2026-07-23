"""anomaly_detection smoke test."""
def test_ad(): from aios_core.anomaly_detection import AnomalyDetector; assert AnomalyDetector().stats() is not None
