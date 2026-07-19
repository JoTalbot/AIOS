"""
AIOS Service Registry Layer v2.1.1

Registers and discovers AIOS services.
"""


class ServiceRegistry:
    def __init__(self):
        self.services = {}

    def register(self, name: str, service: dict):
        self.services[name] = service
        return service

    def discover(self, name: str):
        return self.services.get(name)
