class PlanetaryKernel:
    """AIOS planetary core kernel foundation."""

    def __init__(self):
        self.modules = []

    def register(self, module):
        self.modules.append(module)

    def status(self):
        return self.modules
