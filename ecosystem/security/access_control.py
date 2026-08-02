class AccessControl:
    """Agent permission management foundation."""

    def __init__(self):
        self.permissions = {}

    def grant(self, agent, permission):
        self.permissions.setdefault(agent, []).append(permission)

    def check(self, agent, permission):
        return permission in self.permissions.get(agent, [])
