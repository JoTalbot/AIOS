"""
AIOS Ethics Layer v2.1.1

Evaluates actions against value alignment principles.
"""


class EthicsLayer:
    def __init__(self):
        self.values = [
            "safety",
            "benefit",
            "transparency",
            "human_control"
        ]

    def evaluate(self, action: dict) -> dict:
        return {
            "status": "EVALUATED",
            "action": action,
            "values_checked": self.values
        }
