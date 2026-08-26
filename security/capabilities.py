class CapabilityManager:
    def __init__(self):
        self.permissions = {}

    def grant(self, agent_id, capability):
        self.permissions.setdefault(agent_id, set()).add(capability)

    def allowed(self, agent_id, capability):
        return capability in self.permissions.get(agent_id, set())
