class ContextManager:
    def __init__(self):
        self.sessions = {}

    def create(self, agent_id):
        self.sessions[agent_id] = {
            "short_memory": [],
            "state": {},
            "history": []
        }

    def remember(self, agent_id, data):
        self.sessions[agent_id]["history"].append(data)

    def get(self, agent_id):
        return self.sessions.get(agent_id)
