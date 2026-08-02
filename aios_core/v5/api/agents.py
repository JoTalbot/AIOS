class AgentsAPI:
    """Agent management API foundation."""

    def __init__(self, registry=None):
        self.registry = registry

    def list_agents(self):
        return list(self.registry.keys()) if self.registry else []
