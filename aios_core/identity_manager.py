"""
AIOS Identity Manager Layer v2.1.1

Manages identities of AIOS nodes and agents.
"""


class IdentityManager:
    def __init__(self):
        self.identities = {}

    def register(self, identity_id: str, role: str):
        self.identities[identity_id] = {"role": role, "active": True}
        return self.identities[identity_id]

    def verify(self, identity_id: str):
        return self.identities.get(identity_id)
