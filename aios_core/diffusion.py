"""Diffusion Models for AIOS"""

from typing import List
import random


class DiffusionModel:
    """Simplified diffusion probabilistic model."""

    def __init__(self, timesteps: int = 1000):
        self.timesteps = timesteps
        self.betas = [0.0001 + i * 0.00001 for i in range(timesteps)]

    def forward_process(self, x: List[float], t: int) -> List[float]:
        noise = [random.gauss(0, 1) for _ in x]
        alpha = 1 - sum(self.betas[:t])
        return [a * alpha + n * (1 - alpha) for a, n in zip(x, noise)]

    def sample(self, shape: int) -> List[float]:
        return [random.gauss(0, 1) for _ in range(shape)]

    def stats(self) -> dict:
        return {"timesteps": self.timesteps}
