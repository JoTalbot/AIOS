"""Performance Profiling for AIOS"""

import time
from contextlib import contextmanager
from typing import Dict


class PerformanceProfiler:
    """Simple performance profiler."""

    def __init__(self):
        """Initialize PerformanceProfiler."""
        self.measurements: Dict[str, list] = {}

    @contextmanager
    def measure(self, name: str) -> None:
        """Execute measure."""
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = (time.perf_counter() - start) * 1000
            if name not in self.measurements:
                self.measurements[name] = []
            self.measurements[name].append(duration)

    def stats(self) -> dict:
        """Return statistics dict."""
        result = {}
        for name, times in self.measurements.items():
            result[name] = {
                "count": len(times),
                "avg_ms": round(sum(times) / len(times), 2),
                "max_ms": round(max(times), 2),
                "min_ms": round(min(times), 2),
            }
        return result


profiler = PerformanceProfiler()
