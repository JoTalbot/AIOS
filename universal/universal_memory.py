class UniversalMemory:
    """Universal intelligence memory foundation."""

    def __init__(self):
        self.store = []

    def remember(self, item):
        self.store.append(item)

    def recall(self):
        return self.store
