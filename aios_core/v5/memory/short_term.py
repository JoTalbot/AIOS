class ShortTermMemory:
    def __init__(self):
        self.items = []

    def remember(self, item):
        self.items.append(item)

    def get_all(self):
        return self.items
