from datetime import datetime


class HeartbeatManager:
    def __init__(self):
        self.timestamps = {}

    def ping(self, agent_id):
        self.timestamps[agent_id] = datetime.utcnow()

    def alive(self, agent_id):
        return agent_id in self.timestamps
