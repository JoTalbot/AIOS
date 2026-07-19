"""
AIOS Performance Monitor Layer v2.1.1

Monitors system performance and detects bottlenecks.
"""


class PerformanceMonitor:
    def __init__(self):
        self.performance = []

    def record(self, data: dict):
        self.performance.append(data)
        return data

    def report(self):
        return self.performance
