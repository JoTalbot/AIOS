"""health_checks test."""
from aios_core.health_checks import HealthChecker
def test_init(): s = HealthChecker().stats(); assert isinstance(s, dict)
