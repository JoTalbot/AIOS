class EventOrchestrator:
    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        self.handlers = {}

    def register(self, event, handler):
        self.handlers[event] = handler

    async def dispatch(self, event, payload):
        handler = self.handlers.get(event)
        if handler:
            return await handler(payload)
        return None
