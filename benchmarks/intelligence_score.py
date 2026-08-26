"""AIOS intelligence score benchmark."""


class IntelligenceScore:
    def __init__(self):
        self.metrics = {}

    def update(self, metric, value):
        self.metrics[metric] = value

    def score(self):
        if not self.metrics:
            return 0
        return sum(self.metrics.values()) / len(self.metrics)
