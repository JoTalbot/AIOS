"""AIOS autonomy stability benchmark."""


class AutonomyStabilityTest:
    def __init__(self):
        self.cycles = 0

    def record_cycle(self):
        self.cycles += 1

    def stable(self, minimum=1):
        return self.cycles >= minimum
