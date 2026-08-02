class PermissionManager:
    """Universal permission management foundation."""

    def allow(self, agent, permission):
        return {
            "agent": agent,
            "permission": permission,
            "allowed": True
        }
