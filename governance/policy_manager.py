class PolicyManager:
    """AIOS policy management foundation."""

    def get_policy(self, name):
        return {
            "policy": name,
            "loaded": True
        }
