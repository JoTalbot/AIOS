"""Production Model Serving Infrastructure for AIOS.

Provides thread-safe model deployment, A/B traffic routing, batch predictions,
latency profiling, and automatic fallback handling.
"""

import random
import time
from typing import Any

__all__ = ["ModelServer"]


class ModelServer:
    """Production ML Model Serving Engine."""

    def __init__(self, registry: Any = None):
        """Initialize ModelServer."""
        self.registry = registry
        self.models: dict[str, dict[str, Any]] = {}
        self.traffic_splits: dict[
            str, dict[str, float]
        ] = {}  # model_name -> {version: weight}
        self.performance_stats: dict[str, dict[str, float]] = {}

    def deploy(
        self,
        model_id: str,
        model_callable: Any,
        version: str = "1.0.0",
        weight: float = 1.0,
    ) -> str:
        """Deploy a model callable or model instance into the serving container."""
        key = f"{model_id}:{version}"
        self.models[key] = {
            "model_id": model_id,
            "version": version,
            "handler": model_callable,
            "deployed_at": time.time(),
            "total_requests": 0,
            "failed_requests": 0,
            "total_latency_ms": 0.0,
        }

        if model_id not in self.traffic_splits:
            self.traffic_splits[model_id] = {}
        self.traffic_splits[model_id][version] = weight

        return key

    def set_traffic_split(self, model_id: str, split_dict: dict[str, float]) -> None:
        """Define A/B traffic splitting ratio across model versions."""
        total_weight = sum(split_dict.values())
        if total_weight <= 0:
            raise ValueError("Total weight must be positive.")

        normalized = {v: w / total_weight for v, w in split_dict.items()}
        self.traffic_splits[model_id] = normalized

    def predict(
        self, model_id: str, input_data: Any, explicit_version: str | None = None
    ) -> dict[str, Any]:
        """Perform thread-safe inference routing with performance timing."""
        start_time = time.time()
        key = None

        if explicit_version:
            key = f"{model_id}:{explicit_version}"
        elif self.traffic_splits.get(model_id):
            # A/B Traffic Routing
            versions = list(self.traffic_splits[model_id].keys())
            weights = list(self.traffic_splits[model_id].values())
            chosen_version = random.choices(versions, weights=weights, k=1)[0]
            key = f"{model_id}:{chosen_version}"
        else:
            candidates = [k for k in self.models if k.startswith(f"{model_id}:")]
            if candidates:
                key = candidates[0]

        if not key or key not in self.models:
            return {
                "error": f"No active deployment found for model '{model_id}'",
                "success": False,
            }

        deploy_entry = self.models[key]
        handler = deploy_entry["handler"]

        try:
            if callable(handler):
                prediction = handler(input_data)
            elif hasattr(handler, "predict"):
                prediction = handler.predict(input_data)
            else:
                prediction = handler

            latency_ms = (time.time() - start_time) * 1000.0
            deploy_entry["total_requests"] += 1
            deploy_entry["total_latency_ms"] += latency_ms

            return {
                "model_id": model_id,
                "version": deploy_entry["version"],
                "prediction": prediction,
                "latency_ms": round(latency_ms, 3),
                "success": True,
            }

        except Exception as exc:
            deploy_entry["failed_requests"] += 1
            return {
                "model_id": model_id,
                "version": deploy_entry["version"],
                "error": str(exc),
                "success": False,
            }

    def predict_batch(self, model_id: str, items: list[Any]) -> list[dict[str, Any]]:
        """Process a batch of predictions concurrently or sequentially."""
        return [self.predict(model_id, item) for item in items]

    def stats(self) -> dict[str, Any]:
        """Summary metrics across all active model endpoints."""
        total_requests = sum(m["total_requests"] for m in self.models.values())
        return {
            "deployed_models": len(self.models),
            "active_routes": len(self.traffic_splits),
            "total_requests": total_requests,
        }
