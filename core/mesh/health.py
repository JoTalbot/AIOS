class MeshHealthMonitor:

    def __init__(self):
        self.status = {}

    def update(self, agent, healthy=True):
        self.status[agent] = healthy

    def is_available(self, agent):
        return self.status.get(agent, False)
