"""M8 Predictive Maintenance tests"""

from aios_core.android_predictive import PredictiveMaintenance, RiskLevel
import time

def test_record_and_predict_low_risk():
    pm = PredictiveMaintenance()
    for _ in range(10):
        pm.record_event("emulator-5554", "search", 500, True)
    pred = pm.predict("emulator-5554")
    assert pred.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM)
    assert pred.risk_score < 0.5

def test_high_failure_rate_critical():
    pm = PredictiveMaintenance()
    # Simulate many failures in last 5 min
    for _ in range(15):
        pm.record_event("emulator-5556", "search", 1000, False)
    pred = pm.predict("emulator-5556")
    assert pred.risk_score > 0.3
    assert len(pred.reasons) > 0
    assert len(pred.recommendations) > 0

def test_latency_degradation():
    pm = PredictiveMaintenance()
    # Increasing latency trend
    for i in range(20):
        pm.record_event("emulator-5554", "tap", 500 + i*150, True)
    pred = pm.predict("emulator-5554")
    assert pred.metrics_snapshot["latency_avg"] > 0

def test_health_report():
    pm = PredictiveMaintenance()
    pm.record_event("emulator-5554", "search", 800, True)
    pm.record_event("emulator-5556", "search", 1200, False)
    report = pm.health_report()
    assert "total_devices" in report
    assert report["total_devices"] >= 1

def test_predict_all():
    pm = PredictiveMaintenance()
    pm.record_event("dev1", "search", 100, True)
    pm.record_event("dev2", "search", 200, True)
    all_preds = pm.predict_all_devices()
    assert len(all_preds) >= 2
