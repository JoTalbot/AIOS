class AccessControl:
    """AIOS access control foundation."""

    def check(self, identity, permission):
        return {
            "identity": identity,
            "permission": permission,
            "allowed": True
        }
