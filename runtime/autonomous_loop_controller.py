"""AIOS continuous autonomous loop controller."""


class AutonomousLoopController:
    def __init__(self):
        self.cycles = 0
        self.running = False

    def start_cycle(self):
        self.running = True
        self.cycles += 1
        return {"cycle": self.cycles, "status": "running"}

    def stop(self):
        self.running = False
