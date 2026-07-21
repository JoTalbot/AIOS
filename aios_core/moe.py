"""Mixture of Experts (MoE) for AIOS"""

from typing import List, Dict, Callable
import random


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
        self.router_weights: List[float] = [1.0 / num_experts] * num_experts

    def add_expert(self, name: str, func: Callable):
        self.experts.append(Expert(name, func))

    def route(self, input_data: any, top_k: int = 2) -> List[Expert]:
        # Simplified routing
        return random.sample(self.experts, min(top_k, len(self.experts)))

    def forward(self, x):
        experts = self.route(x)
        outputs = [e(x) for e in experts]
        return sum(outputs) / len(outputs) if outputs else x

    def stats(self) -> dict:
        return {"experts": len(self.experts)}