"""Advanced Health Checks for AIOS"""

import time
from typing import Any, Callable, Dict


class HealthCheckRegistry:
    """Registry of health checks."""

    def __init__(self):
        """Initialize HealthCheckRegistry."""
        self.checks: Dict[str, Callable] = {}

    def register(self, name: str, check_func: Callable) -> None:
        """Execute register."""
        self.checks[name] = check_func

    def run_all(self) -> dict[str, Any]:
        """Execute run all."""
        results = {}
        for name, func in self.checks.items():
            try:
                start = time.time()
                result = func()
                duration = (time.time() - start) * 1000
                results[name] = {
                    "status": "healthy" if result else "unhealthy",
                    "duration_ms": round(duration, 2),
                    "details": result if isinstance(result, dict) else {},
                }
            except Exception as e:
                results[name] = {"status": "error", "error": str(e)}
        return results

    def overall_status(self) -> str:
        """Execute overall status."""
        results = self.run_all()
        unhealthy = [k for k, v in results.items() if v.get("status") != "healthy"]
        return "healthy" if not unhealthy else "degraded"


health_registry = HealthCheckRegistry()
