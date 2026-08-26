class AgentStressTest:
    def __init__(self, agents=None):
        self.agents = agents or []
        self.results = []

    def run(self, tasks):
        for agent in self.agents:
            for task in tasks:
                self.results.append({
                    "agent": agent,
                    "task": task,
                    "status": "completed"
                })
        return self.results
