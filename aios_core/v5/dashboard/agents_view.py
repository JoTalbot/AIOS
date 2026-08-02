class AgentsView:
    """Agent status view foundation."""

    def render(self, agents=None):
        return {
            "agents": agents or []
        }
