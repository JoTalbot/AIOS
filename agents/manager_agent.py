"""Manager agent for AIOS swarm coordination."""


class ManagerAgent:
    def __init__(self):
        self.agents = []

    def register(self, agent):
        self.agents.append(agent)

    def status(self):
        return {"agents": len(self.agents)}

    def coordinate(self, task):
        return {"task": task, "assigned": len(self.agents)}
