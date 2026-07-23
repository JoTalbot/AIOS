"""API Gateway for AIOS"""

from typing import Any, Callable, Dict


class APIGateway:
    """Central API Gateway with routing and middleware."""

    def __init__(self):
        self.routes: Dict[str, Callable] = {}
        self.middleware: list = []

    def register(self, path: str, handler: Callable) -> None:
        """Execute register."""
        self.routes[path] = handler

    def add_middleware(self, middleware: Callable) -> None:
        """Execute add middleware."""
        self.middleware.append(middleware)

    def handle(self, path: str, request: Dict) -> Dict:
        """Execute handle."""
        for mw in self.middleware:
            request = mw(request)

        handler = self.routes.get(path)
        if handler:
            return handler(request)
        return {"error": "Not found", "status": 404}

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"routes": len(self.routes), "middleware": len(self.middleware)}
