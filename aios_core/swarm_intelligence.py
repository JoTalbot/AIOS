"""Swarm Intelligence for AIOS"""

import random
from typing import Dict, List


class Particle:
    def __init__(self, position: list[float]):
        self.position = position
        self.velocity = [random.uniform(-1, 1) for _ in position]
        self.best_position = position[:]
        self.best_value = float("inf")

    def update(self, global_best: list[float], w=0.7, c1=1.5, c2=1.5) -> None:
        """Execute update."""
        for i in range(len(self.position)):
            r1, r2 = random.random(), random.random()
            self.velocity[i] = (
                w * self.velocity[i]
                + c1 * r1 * (self.best_position[i] - self.position[i])
                + c2 * r2 * (global_best[i] - self.position[i])
            )
            self.position[i] += self.velocity[i]


class ParticleSwarmOptimizer:
    """PSO for optimization problems."""

    def __init__(self, num_particles: int = 20, dimensions: int = 5):
        self.particles = [
            Particle([random.uniform(-10, 10) for _ in range(dimensions)])
            for _ in range(num_particles)
        ]
        self.global_best = self.particles[0].position[:]
        self.global_best_value = float("inf")

    def optimize(self, fitness_func, iterations: int = 100) -> None:
        """Execute optimize."""
        for _ in range(iterations):
            for p in self.particles:
                value = fitness_func(p.position)
                if value < p.best_value:
                    p.best_value = value
                    p.best_position = p.position[:]
                if value < self.global_best_value:
                    self.global_best_value = value
                    self.global_best = p.position[:]
                p.update(self.global_best)
        return self.global_best, self.global_best_value

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"particles": len(self.particles)}
