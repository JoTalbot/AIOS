"""
AIOS Resource Management Layer v2.1.1

Manages allocation and tracking of AIOS resources.
"""


class ResourceManager:
    def __init__(self):
        self.resources = {}

    def register(self, name: str, amount):
        self.resources[name] = amount
        return {"resource": name, "amount": amount}

    def available(self, name: str):
        return self.resources.get(name, 0)
