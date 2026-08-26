"""Tool supervisor foundation for AIOS runtime."""

class ToolSupervisor:
    def __init__(self, registry=None):
        self.registry = registry
        self.running = False

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def resolve(self, name):
        if self.registry:
            return self.registry.get(name)
        return None
