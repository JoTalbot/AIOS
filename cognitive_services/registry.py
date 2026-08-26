"""AIOS v21.8 Cognitive Service Registry.

Central registration point for cognitive services while keeping
runtime boundaries isolated.
"""


class CognitiveServiceRegistry:
    def __init__(self):
        self._services = {}

    def register(self, service):
        self._services[service.service_name] = service

    def get(self, name):
        return self._services.get(name)

    def health(self):
        return {name: service.health() for name, service in self._services.items()}
