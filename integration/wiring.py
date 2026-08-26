"""AIOS component wiring layer.

Connects services, runtime, agents, tools and memory adapters.
"""

class IntegrationWiring:
    def __init__(self, runtime=None, services=None):
        self.runtime = runtime
        self.services = services or {}

    def register(self, name, component):
        self.services[name] = component

    def get(self, name):
        return self.services.get(name)
