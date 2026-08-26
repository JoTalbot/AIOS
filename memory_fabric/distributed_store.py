class DistributedContextStore:
    def __init__(self):
        self.contexts = {}

    async def set(self, key, value):
        self.contexts[key] = value

    async def get(self, key):
        return self.contexts.get(key)

    async def snapshot(self):
        return self.contexts.copy()
