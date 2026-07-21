"""Model Registry for AIOS"""

from typing import Dict, Any


class ModelRegistry:
    """Registry for ML models."""

    def __init__(self):
        self.models: Dict[str, Dict] = {}

    def register(self, name: str, version: str, metadata: Dict):
        key = f"{name}:{version}"
        self.models[key] = {
            "name": name,
            "version": version,
            "metadata": metadata,
            "status": "registered"
        }

    def get(self, name: str, version: str = "latest") -> Dict:
        if version == "latest":
            versions = [k for k in self.models if k.startswith(name)]
            if versions:
                return self.models[max(versions)]
        return self.models.get(f"{name}:{version}")

    def promote(self, name: str, version: str):
        key = f"{name}:{version}"
        if key in self.models:
            self.models[key]["status"] = "production"

    def stats(self) -> dict:
        return {"models": len(self.models)}