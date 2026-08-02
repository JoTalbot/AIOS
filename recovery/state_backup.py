class StateBackup:
    """AIOS state backup foundation."""

    def backup(self, state):
        return {
            "state": state,
            "backup": True
        }
