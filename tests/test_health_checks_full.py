"""Health checks full."""
from aios_core.health_checks import HealthChecker
def test(): s=HealthChecker().stats(); assert isinstance(s,dict)
