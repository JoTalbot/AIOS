"""AIOS Metrics Engine"""

class MetricsEngine:
    def __init__(self):
        self.metrics = {}

    def record(self, name, value):
        self.metrics[name] = value
        return True

    def get_metrics(self):
        return self.metrics
