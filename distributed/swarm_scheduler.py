class SwarmScheduler:
    def __init__(self):
        self.agents = []

    def register(self, agent):
        self.agents.append(agent)

    def dispatch(self, task):
        if not self.agents:
            return None
        return self.agents[0], task
