"""
AIOS Metrics Collector Layer v2.1.1

Collects operational metrics from AIOS components.
"""


class MetricsCollector:
    def __init__(self):
        self.metrics = {}

    def record(self, name: str, value):
        self.metrics[name] = value
        return {"metric": name, "value": value}

    def snapshot(self):
        return self.metrics
