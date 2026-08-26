"""Context manager foundation for AIOS memory layer."""


class ContextManager:
    def __init__(self):
        self.contexts = {}

    async def set(self, key, value):
        self.contexts[key] = value

    async def get(self, key, default=None):
        return self.contexts.get(key, default)

    async def clear(self, key):
        self.contexts.pop(key, None)
