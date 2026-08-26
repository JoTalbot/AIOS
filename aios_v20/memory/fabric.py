"""AIOS v20 Memory Fabric.

Separates local, shared and governance memory domains.
"""


class MemoryFabric:
    def __init__(self):
        self.local = {}
        self.shared = {}
        self.governance = {}

    def store(self, domain, key, value):
        getattr(self, domain)[key] = value

    def retrieve(self, domain, key):
        return getattr(self, domain).get(key)
