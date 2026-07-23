"""Diffusion Models for AIOS"""

import random
from typing import List

__all__ = ["DiffusionModel"]


class DiffusionModel:
    """Simplified diffusion probabilistic model with forward process and sampling."""
    __slots__ = ()

    def __init__(self, timesteps: int = 1000):
        self.timesteps = timesteps
        self.betas = [0.0001 + i * 0.00001 for i in range(timesteps)]

    def forward_process(self, x: List[float], t: int) -> List[float]:
        """Apply forward diffusion at timestep *t* to input *x*."""
        noise = [random.gauss(0, 1) for _ in x]
        alpha = 1 - sum(self.betas[:t])
        return [a * alpha + n * (1 - alpha) for a, n in zip(x, noise)]

    def sample(self, shape: int) -> List[float]:
        """Generate *shape* random samples from the prior distribution."""
        return [random.gauss(0, 1) for _ in range(shape)]

    def stats(self) -> dict:
        """Return number of diffusion timesteps."""
        return {"timesteps": self.timesteps}
