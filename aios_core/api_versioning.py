"""API Versioning for AIOS"""

from typing import Callable, Dict

from starlette.responses import JSONResponse


class APIVersioning:
    """Simple API versioning middleware."""

    def __init__(self):
        self.versions: Dict[str, Dict] = {}

    def register(self, version: str, routes: Dict) -> None:
        self.versions[version] = routes

    def get_version(self, request) -> str:
        # Check header or path
        return request.headers.get("X-API-Version", "v1")

    def route(self, version: str, path: str) -> None:
        def decorator(func: Callable) -> None:
            if version not in self.versions:
                self.versions[version] = {}
            self.versions[version][path] = func
            return func

        return decorator


api_versioning = APIVersioning()
