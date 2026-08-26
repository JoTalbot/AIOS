"""AIOS Debate Agent for collaborative decision review."""


class DebateAgent:
    def __init__(self, name="critic"):
        self.name = name

    def evaluate(self, proposal):
        return {"proposal": proposal, "status": "reviewed", "agent": self.name}
