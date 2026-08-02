class CivilizationKernel:
    """AIOS civilization core kernel foundation."""

    def __init__(self):
        self.layers = []

    def register(self, layer):
        self.layers.append(layer)

    def status(self):
        return self.layers
