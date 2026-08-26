class ShortTermMemory:
    def __init__(self):
        self.context = []

    def add(self, item):
        self.context.append(item)

    def get_all(self):
        return self.context
