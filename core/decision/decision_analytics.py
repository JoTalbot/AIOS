class DecisionRecord:
    def __init__(self, agent_id, score, decision):
        self.agent_id = agent_id
        self.score = score
        self.decision = decision


class DecisionAnalytics:
    def __init__(self):
        self.history = []

    def record(self, agent_id, score, decision):
        self.history.append(DecisionRecord(agent_id, score, decision))

    def get_history(self):
        return self.history

    def best_decision(self):
        if not self.history:
            return None
        return max(self.history, key=lambda item: item.score)
