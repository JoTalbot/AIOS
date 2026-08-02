class ResourceManager:
    """Ecosystem resource allocation foundation."""

    def __init__(self):
        self.resources = {}

    def allocate(self, agent, resource):
        self.resources[agent] = resource

    def get(self, agent):
        return self.resources.get(agent)
