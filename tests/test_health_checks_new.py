"""health_checks test."""
def test(): from aios_core.health_checks import HealthChecker; s = HealthChecker().stats(); assert isinstance(s, dict)
