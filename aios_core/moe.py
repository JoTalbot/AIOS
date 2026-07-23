"""Mixture of Experts (MoE) for AIOS"""

import random
from typing import Callable, Dict, List


class Expert:
    def __init__(self, name: str, func: Callable):
        self.name = name
        self.func = func
        self.usage = 0

    def __call__(self, x):
        self.usage += 1
        return self.func(x)


class MixtureOfExperts:
    """Dynamic Mixture of Experts routing."""

    def __init__(self, num_experts: int = 8):
        self.experts: List[Expert] = []
        self.router_weights: list[float] = [1.0 / num_experts] * num_experts

    def add_expert(self, name: str, func: Callable) -> None:
        """Execute add expert."""
        self.experts.append(Expert(name, func))

    def route(self, input_data: any, top_k: int = 2) -> List[Expert]:
        """Execute route."""
        # Simplified routing
        return random.sample(self.experts, min(top_k, len(self.experts)))

    def forward(self, x) -> None:
        """Execute forward."""
        experts = self.route(x)
        outputs = [e(x) for e in experts]
        return sum(outputs) / len(outputs) if outputs else x

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"experts": len(self.experts)}
