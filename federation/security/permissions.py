class PermissionManager:
    """Federation access control foundation."""

    def __init__(self):
        self.permissions = {}

    def grant(self, identity, permission):
        self.permissions.setdefault(identity, []).append(permission)

    def check(self, identity, permission):
        return permission in self.permissions.get(identity, [])
