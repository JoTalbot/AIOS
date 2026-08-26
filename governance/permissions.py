class RuntimePermissionModel:

    def __init__(self):
        self.permissions = {}

    def grant(self, agent, capability):
        self.permissions.setdefault(agent, set()).add(capability)

    def allowed(self, agent, capability):
        return capability in self.permissions.get(agent, set())
