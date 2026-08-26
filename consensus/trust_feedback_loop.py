"""Agent trust feedback loop.

Connects evaluation results with dynamic consensus weighting.
"""


class TrustFeedbackEvent:
    def __init__(self, agent_id: str, reward: float, success: bool):
        self.agent_id = agent_id
        self.reward = reward
        self.success = success


class TrustFeedbackLoop:
    def __init__(self, weighting):
        self.weighting = weighting

    def process(self, event: TrustFeedbackEvent):
        delta = event.reward if event.success else -abs(event.reward)
        return self.weighting.update_weight(event.agent_id, delta)
