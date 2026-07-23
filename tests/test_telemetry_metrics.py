from aios_core.telemetry import Telemetry
def test_metrics():
    t = Telemetry()
    assert t.stats() is not None