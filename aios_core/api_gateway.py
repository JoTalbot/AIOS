"""
AIOS API Gateway Layer v2.1.1

Provides a unified access point for AIOS services.
"""


class APIGateway:
    def __init__(self):
        self.routes = {}

    def register_route(self, name: str, handler):
        self.routes[name] = handler
        return name

    def list_routes(self):
        return self.routes
