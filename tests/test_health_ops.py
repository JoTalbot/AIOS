"""Health checker operations tests."""
from aios_core.health_checks import HealthChecker
def test_health_ops():
    hc = HealthChecker()
    assert hc.stats() is not None
