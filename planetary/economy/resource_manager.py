class ResourceManager:
    """Planetary resource management foundation."""

    def __init__(self):
        self.resources = {}

    def allocate(self, resource, amount):
        self.resources[resource] = amount

    def status(self):
        return self.resources
