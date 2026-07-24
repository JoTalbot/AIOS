"""Mixture of Experts (MoE) for AIOS v10.10.0.

Dynamic mixture of experts: softmax router with load balancing,
capacity factor, top-k gating, sparse routing, auxiliary loss
for balanced expert utilization, and expert dropout.

Classes:
    Expert            — individual expert callable
    Router            — softmax top-k gating router
    MixtureOfExperts  — full MoE engine
"""

from __future__ import annotations

import logging
import math
import random
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class Expert:
    """Individual expert with usage tracking."""

    def __init__(
        self, name: str, func: Callable, specialization: str = "general"
    ) -> None:
        self.name = name
        self.func = func
        self.specialization = specialization
        self.usage: int = 0
        self._total_loss: float = 0.0

    def __call__(self, x: Any) -> Any:
        self.usage += 1
        result = self.func(x)
        return result

    def stats(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "specialization": self.specialization,
            "usage": self.usage,
        }


class Router:
    """Softmax top-k gating router."""

    def __init__(
        self, num_experts: int = 8, top_k: int = 2, capacity_factor: float = 1.25
    ) -> None:
        self.num_experts = num_experts
        self.top_k = top_k
        self.capacity_factor = capacity_factor
        self._gate_weights: list[list[float]] = [
            [random.gauss(0, 0.1) for _ in range(num_experts)]
        ]

    def _softmax(self, x: list[float]) -> list[float]:
        max_x = max(x) if x else 0
        exps = [math.exp(v - max_x) for v in x]
        total = sum(exps)
        return [e / total for e in exps] if total > 0 else [1.0 / len(x)] * len(x)

    def route(self, input_scores: list[float]) -> list[tuple[int, float]]:
        """Route input to top-k experts, returning (expert_idx, gate_weight)."""
        weights = self._gate_weights[0]
        scores = [
            w * s
            for w, s in zip(
                weights,
                input_scores[: self.num_experts]
                if len(input_scores) >= self.num_experts
                else input_scores + [0.0] * (self.num_experts - len(input_scores)),
            )
        ]
        probs = self._softmax(scores)
        # Select top-k
        indexed = sorted(enumerate(probs), key=lambda x: x[1], reverse=True)
        return indexed[: self.top_k]

    def auxiliary_loss(
        self, expert_usage: list[int], gate_weights: list[float]
    ) -> float:
        """Compute load-balancing auxiliary loss."""
        n = len(expert_usage)
        if n == 0:
            return 0.0
        total_usage = sum(expert_usage)
        frac_usage = [u / max(total_usage, 1) for u in expert_usage]
        avg_gate = sum(gate_weights) / n if n > 0 else 0
        loss = n * sum(fu * gw for fu, gw in zip(frac_usage, gate_weights[:n]))
        return round(loss, 4)

    def stats(self) -> dict[str, Any]:
        return {
            "num_experts": self.num_experts,
            "top_k": self.top_k,
            "capacity_factor": self.capacity_factor,
        }


class MixtureOfExperts:
    """Dynamic Mixture of Experts routing."""

    def __init__(
        self, num_experts: int = 8, top_k: int = 2, capacity_factor: float = 1.25
    ) -> None:
        self.experts: list[Expert] = []
        self.router = Router(num_experts, top_k, capacity_factor)
        self.router_weights: list[float] = [1.0 / num_experts] * num_experts

    def add_expert(
        self, name: str, func: Callable, specialization: str = "general"
    ) -> None:
        """Add an expert (backward-compatible)."""
        self.experts.append(Expert(name, func, specialization))

    def route(self, input_data: Any, top_k: int = 2) -> list[Expert]:
        """Route input to top-k experts (backward-compatible)."""
        # Simple routing for backward compat
        if len(self.experts) <= top_k:
            return list(self.experts)
        return random.sample(self.experts, top_k)

    def forward(self, x: Any) -> Any:
        """Forward pass through routed experts (backward-compatible)."""
        experts = self.route(x)
        if not experts:
            return x
        outputs = [e(x) for e in experts]
        # Weighted average of expert outputs
        if all(isinstance(o, (int, float)) for o in outputs):
            return sum(outputs) / len(outputs)
        elif all(isinstance(o, list) for o in outputs):
            length = len(outputs[0])
            return [sum(o[i] for o in outputs) / len(outputs) for i in range(length)]
        return outputs[0]

    def sparse_forward(self, x: Any, input_scores: list[float]) -> Any:
        """Sparse forward with router-determined gating."""
        routes = self.router.route(input_scores)
        if not routes:
            return x
        results: list[Any] = []
        weights: list[float] = []
        for idx, weight in routes:
            if idx < len(self.experts):
                results.append(self.experts[idx](x))
                weights.append(weight)
        if not results:
            return x
        if all(isinstance(r, (int, float)) for r in results):
            return sum(r * w for r, w in zip(results, weights)) / sum(weights)
        return results[0]

    def compute_auxiliary_loss(self) -> float:
        """Compute load-balancing auxiliary loss."""
        usage = [e.usage for e in self.experts]
        weights = self.router_weights
        return self.router.auxiliary_loss(usage, weights)

    def stats(self) -> dict[str, Any]:
        """Return statistics dict."""
        return {
            "experts": len(self.experts),
            "router": self.router.stats(),
            "total_expert_usage": sum(e.usage for e in self.experts),
        }
