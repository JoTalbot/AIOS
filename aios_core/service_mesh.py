"""Basic Service Mesh for AIOS"""

from typing import Dict, List


class ServiceMesh:
    """Simple service mesh for inter-service communication."""

    def __init__(self):
        """Initialize ServiceMesh."""
        self.services: dict[str, dict] = {}
        self.routes: List[Dict] = []

    def register_service(self, name: str, endpoint: str, metadata: Dict = None) -> None:
        """Execute register service."""
        self.services[name] = {
            "endpoint": endpoint,
            "metadata": metadata or {},
            "status": "healthy",
        }

    def add_route(self, source: str, target: str, weight: int = 100) -> None:
        """Execute add route."""
        self.routes.append({"source": source, "target": target, "weight": weight})

    def discover(self, service: str) -> Dict:
        """Execute discover."""
        return self.services.get(service, {})

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"services": len(self.services), "routes": len(self.routes)}


service_mesh = ServiceMesh()
