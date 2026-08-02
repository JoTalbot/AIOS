class MetricsCollector:
    """Production metrics collection foundation."""

    def __init__(self):
        self.metrics = {}

    def record(self, name, value):
        self.metrics[name] = value

    def all(self):
        return self.metrics
