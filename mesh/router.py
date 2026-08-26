class AgentRouter:

    def __init__(self):
        self.routes = {}

    def register(self, agent_name, handler):
        self.routes[agent_name] = handler

    async def send(self, packet):
        handler = self.routes.get(packet.receiver)
        if not handler:
            raise ValueError("Agent route unavailable")
        return await handler(packet)
