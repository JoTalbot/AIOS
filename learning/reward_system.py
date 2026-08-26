class RewardSystem:
    def __init__(self):
        self.scores = {}

    def evaluate(self, agent_id, result):
        score = 1 if result else 0
        self.scores.setdefault(agent_id, []).append(score)
        return score

    def history(self, agent_id):
        return self.scores.get(agent_id, [])
