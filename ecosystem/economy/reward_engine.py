class RewardEngine:
    """Agent reward calculation foundation."""

    def reward(self, agent, contribution):
        return {
            "agent": agent,
            "contribution": contribution,
            "reward": 0
        }
