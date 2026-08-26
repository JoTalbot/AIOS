"""AIOS autonomy dashboard metrics."""


class AutonomyDashboard:
    def __init__(self):
        self.metrics = {}

    def update(self, name, value):
        self.metrics[name] = value

    def report(self):
        return dict(self.metrics)
