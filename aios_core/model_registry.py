"""Advanced ML Model Registry for AIOS Executive Layer.

Supports ONNX, scikit-learn, PyTorch/TensorFlow metadata, weight hashing,
version lineage, stage promotion, and metric tracking.
"""

import hashlib
import json
import time
from typing import Dict, List, Optional, Any, Tuple


class ModelRegistry:
    """Enterprise ML Model Registry with strict stage management and verification."""

    def __init__(self):
        self.models: Dict[str, Dict[str, Any]] = {}  # key: "name:version"
        self.stage_routes: Dict[str, Dict[str, str]] = {}  # name -> stage -> version

    def register_model(
        self,
        name: str,
        version: str,
        framework: str,
        metadata: Optional[Dict[str, Any]] = None,
        artifact_bytes: Optional[bytes] = None,
        stage: str = "staging",
    ) -> Dict[str, Any]:
        """Register a new model version in the registry."""
        key = f"{name}:{version}"
        sha256_hash = (
            hashlib.sha256(artifact_bytes).hexdigest() if artifact_bytes else "no_hash"
        )

        entry = {
            "name": name,
            "version": version,
            "framework": framework,
            "metadata": metadata or {},
            "sha256": sha256_hash,
            "artifact_size": len(artifact_bytes) if artifact_bytes else 0,
            "stage": stage,
            "created_at": time.time(),
            "updated_at": time.time(),
            "eval_metrics": {},
            "prediction_count": 0,
        }

        self.models[key] = entry

        if name not in self.stage_routes:
            self.stage_routes[name] = {}
        self.stage_routes[name][stage] = version

        return entry

    def register(self, name: str, version: str, metadata: Dict) -> Dict[str, Any]:
        """Backward-compatible registry wrapper."""
        framework = metadata.get("framework", "custom")
        return self.register_model(
            name=name, version=version, framework=framework, metadata=metadata
        )

    def promote(self, name: str, version: str, stage: str = "production") -> bool:
        """Promote a model version to a target stage (e.g., 'production', 'archived')."""
        key = f"{name}:{version}"
        if key not in self.models:
            return False

        old_stage = self.models[key]["stage"]
        self.models[key]["stage"] = stage
        self.models[key]["updated_at"] = time.time()

        if name not in self.stage_routes:
            self.stage_routes[name] = {}

        self.stage_routes[name][stage] = version
        return True

    def get_model(
        self, name: str, version_or_stage: str = "production"
    ) -> Optional[Dict[str, Any]]:
        """Retrieve model metadata by explicit version or stage name."""
        if name in self.stage_routes and version_or_stage in self.stage_routes[name]:
            target_version = self.stage_routes[name][version_or_stage]
            return self.models.get(f"{name}:{target_version}")

        key = f"{name}:{version_or_stage}"
        if key in self.models:
            return self.models[key]

        if version_or_stage == "latest":
            matching = [v for k, v in self.models.items() if v["name"] == name]
            if matching:
                return max(matching, key=lambda x: x["created_at"])

        return None

    def get(self, name: str, version: str = "latest") -> Optional[Dict[str, Any]]:
        """Backward-compatible fetcher."""
        return self.get_model(name, version)

    def log_evaluation_metrics(
        self, name: str, version: str, metrics: Dict[str, float]
    ) -> bool:
        """Log accuracy, latency, F1, or MSE evaluation metrics for a model version."""
        key = f"{name}:{version}"
        if key not in self.models:
            return False

        self.models[key]["eval_metrics"].update(metrics)
        self.models[key]["updated_at"] = time.time()
        return True

    def list_versions(self, name: str) -> List[Dict[str, Any]]:
        """List all registered versions for a specific model name."""
        return [v for k, v in self.models.values() if v["name"] == name]

    def stats(self) -> Dict[str, Any]:
        """Return registry aggregate statistics."""
        production_count = sum(
            1 for v in self.models.values() if v["stage"] == "production"
        )
        return {
            "total_models": len(self.models),
            "production_models": production_count,
            "registered_names": list(self.stage_routes.keys()),
        }
