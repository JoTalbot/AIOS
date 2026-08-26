class AutonomousManager:
    def __init__(self, components=None):
        self.components = components or {}
        self.mode = "observe"

    def set_mode(self, mode):
        self.mode = mode

    def run_cycle(self, goal):
        return {
            "goal": goal,
            "mode": self.mode,
            "status": "cycle_started"
        }
