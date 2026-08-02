class ActionSelector:
    """Autonomous action selection foundation."""

    def select(self, actions):
        return actions[0] if actions else None
