class DecisionBridge:
    """Bridge between OLX observations and agent decisions."""

    def decide(self, observation):
        return {
            "observation": observation,
            "next_action": "analyze"
        }
