"""Event replay foundation."""

class EventReplay:
    def __init__(self, store=None):
        self.store = store

    async def replay(self, execution_id):
        if self.store is None:
            return []
        return await self.store.load(execution_id)
