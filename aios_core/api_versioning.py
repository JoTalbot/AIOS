"""API Versioning for AIOS"""

from typing import Dict, Callable
from starlette.responses import JSONResponse


class APIVersioning:
    """Simple API versioning middleware."""

    def __init__(self):
        self.versions: Dict[str, Dict] = {}

    def register(self, version: str, routes: Dict):
        self.versions[version] = routes

    def get_version(self, request) -> str:
        # Check header or path
        return request.headers.get("X-API-Version", "v1")

    def route(self, version: str, path: str):
        def decorator(func: Callable):
            if version not in self.versions:
                self.versions[version] = {}
            self.versions[version][path] = func
            return func

        return decorator


api_versioning = APIVersioning()
