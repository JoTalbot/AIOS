class AutonomyScore:
    def __init__(self):
        self.metrics = {}

    def record(self, name, value):
        self.metrics[name] = value

    def calculate(self):
        if not self.metrics:
            return 0
        return sum(self.metrics.values()) / len(self.metrics)
