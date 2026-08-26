class KernelRegistry:
    def __init__(self):
        self.components = {}

    def register(self, name, component):
        self.components[name] = component

    def get(self, name):
        return self.components.get(name)

    def list_components(self):
        return list(self.components.keys())

    def restore(self, recovery):
        recovery.restore(self)
        return self
