class Sandbox:
    def __init__(self):
        self.permissions = {}

    def grant(self, agent_id, capability):
        self.permissions.setdefault(agent_id, set()).add(capability)

    def allowed(self, agent_id, capability):
        return capability in self.permissions.get(agent_id, set())

    def execute(self, agent_id, capability, action):
        if not self.allowed(agent_id, capability):
            raise PermissionError("AIOS sandbox denied capability")
        return action()
