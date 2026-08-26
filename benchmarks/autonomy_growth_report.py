"""AIOS autonomy growth tracking benchmark."""


class AutonomyGrowthReport:
    def __init__(self):
        self.history = []

    def add_cycle(self, score, version=None):
        self.history.append({"version": version, "score": score})

    def latest(self):
        return self.history[-1] if self.history else None
