"""
AIOS Decision Engine Layer v2.1.1

Creates decisions using AIOS rules and available information.
"""


class DecisionEngine:
    def __init__(self):
        self.decisions = []

    def decide(self, context: dict):
        decision = {
            "context": context,
            "status": "evaluated"
        }
        self.decisions.append(decision)
        return decision

    def history(self):
        return self.decisions
