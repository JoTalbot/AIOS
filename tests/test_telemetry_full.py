"""Telemetry full tests."""
from aios_core.telemetry import Telemetry
def test_telemetry_stats():
    t = Telemetry()
    assert t.stats() is not None
