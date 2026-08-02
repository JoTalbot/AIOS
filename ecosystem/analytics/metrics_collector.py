class MetricsCollector:
    """Ecosystem metrics collection foundation."""

    def __init__(self):
        self.metrics = []

    def collect(self, metric):
        self.metrics.append(metric)

    def get(self):
        return self.metrics
