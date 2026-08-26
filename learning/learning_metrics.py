class LearningMetrics:
    def __init__(self):
        self.metrics = []

    def add(self, metric):
        self.metrics.append(metric)

    def latest(self):
        return self.metrics[-1] if self.metrics else None
