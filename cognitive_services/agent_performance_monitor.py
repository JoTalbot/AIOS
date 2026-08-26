"""AIOS v22.9 Agent Performance Monitor foundation."""


class AgentPerformanceMonitor:
    def __init__(self):
        self.metrics = []

    def record(self, metric):
        self.metrics.append(metric)

    def summary(self):
        return {"count": len(self.metrics)}
