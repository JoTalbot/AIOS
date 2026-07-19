"""
AIOS Access Control Layer v2.1.1

Manages roles and permissions.
"""


class AccessControl:
    def __init__(self):
        self.permissions = {}

    def grant(self, identity: str, permission: str):
        self.permissions.setdefault(identity, []).append(permission)
        return self.permissions[identity]

    def check(self, identity: str, permission: str):
        return permission in self.permissions.get(identity, [])
