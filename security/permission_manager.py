class PermissionManager:
    """AIOS permission management foundation."""

    def grant(self, agent, permission):
        return {
            "agent": agent,
            "permission": permission,
            "granted": True
        }
