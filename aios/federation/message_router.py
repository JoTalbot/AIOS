"""Federation message routing."""


class MessageRouter:
    def __init__(self):
        self.routes = {}

    def register(self, node_id, handler):
        self.routes[node_id] = handler

    def route(self, node_id, message):
        handler = self.routes.get(node_id)
        if handler is None:
            return None
        return handler(message)
