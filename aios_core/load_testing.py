"""Load Testing Framework for AIOS"""

import logging
import threading
import time
from typing import Callable, Dict

logger = logging.getLogger(__name__)


class LoadTester:
    """Simple concurrent load tester."""

    def __init__(self):
        self.results = []

    def run(self, func: Callable, concurrent_users: int = 10, duration_seconds: int = 30):
        self.results = []
        start_time = time.time()

        def worker():
            while time.time() - start_time < duration_seconds:
                try:
                    start = time.perf_counter()
                    func()
                    latency = (time.perf_counter() - start) * 1000
                    self.results.append(latency)
                except Exception:
                    pass

        threads = [threading.Thread(target=worker) for _ in range(concurrent_users)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        if not self.results:
            return {"error": "No successful requests"}

        return {
            "requests": len(self.results),
            "avg_latency_ms": round(sum(self.results) / len(self.results), 2),
            "max_latency_ms": round(max(self.results), 2),
            "rps": round(len(self.results) / duration_seconds, 2),
        }

    def stats(self) -> dict:
        return {"tests_run": len(self.results)}
