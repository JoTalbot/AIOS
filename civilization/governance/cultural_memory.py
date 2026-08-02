class CulturalMemory:
    """Civilization cultural memory foundation."""

    def __init__(self):
        self.values = []

    def preserve(self, value):
        self.values.append(value)

    def retrieve(self):
        return self.values
