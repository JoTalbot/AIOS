class MetricsCollector:
    """AIOS metrics collection foundation."""

    def __init__(self):
        self.metrics = {}

    def record(self, key, value):
        self.metrics[key] = value

    def get(self, key):
        return self.metrics.get(key)
