class AgentEvaluation:
    def __init__(self, agent_id: str, score: float, metrics: dict | None = None):
        self.agent_id = agent_id
        self.score = score
        self.metrics = metrics or {}


class AgentEvaluator:
    def __init__(self):
        self.history = {}

    def evaluate(self, agent_id: str, success: bool, reward: float):
        current = self.history.get(agent_id, 0.0)
        updated = (current + reward) / 2
        if success:
            updated = max(updated, reward)
        self.history[agent_id] = updated
        return AgentEvaluation(
            agent_id=agent_id,
            score=updated,
            metrics={"success": success, "reward": reward},
        )

    def confidence(self, agent_id: str) -> float:
        return self.history.get(agent_id, 0.0)
