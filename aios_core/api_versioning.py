"""API Versioning for AIOS"""

from typing import Callable, Dict

from starlette.responses import JSONResponse


class APIVersioning:
    """Simple API versioning middleware."""

    def __init__(self):
        """Initialize APIVersioning."""
        self.versions: dict[str, dict] = {}

    def register(self, version: str, routes: Dict) -> None:
        """Execute register."""
        self.versions[version] = routes

    def get_version(self, request) -> str:
        """Execute get version."""
        # Check header or path
        return request.headers.get("X-API-Version", "v1")

    def route(self, version: str, path: str) -> None:
        """Execute route."""
        def decorator(func: Callable) -> None:
            """Execute decorator."""
            if version not in self.versions:
                self.versions[version] = {}
            self.versions[version][path] = func
            return func

        return decorator


api_versioning = APIVersioning()
