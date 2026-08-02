class ActionSelector:
    """AIOS action selection foundation."""

    def select(self, actions):
        return {
            "action": actions[0] if actions else None,
            "selected": True
        }
