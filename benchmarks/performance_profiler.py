"""Performance profiler for AIOS autonomous cycles."""


class PerformanceProfiler:
    def __init__(self):
        self.metrics = []

    def record(self, cycle, duration):
        self.metrics.append({"cycle": cycle, "duration": duration})

    def report(self):
        return self.metrics
