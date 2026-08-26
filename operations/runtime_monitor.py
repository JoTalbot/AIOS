from dataclasses import dataclass

@dataclass
class RuntimeMetric:
    name: str
    value: float

class RuntimeMonitor:
    def __init__(self):
        self.metrics = []

    def record(self, metric):
        self.metrics.append(metric)

    def health(self):
        if not self.metrics:
            return 1.0
        return sum(m.value for m in self.metrics) / len(self.metrics)
