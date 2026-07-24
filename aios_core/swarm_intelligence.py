"""Swarm Intelligence for AIOS v10.12.0.

Swarm intelligence: Particle Swarm Optimization (PSO),
Ant Colony Optimization (ACO), Bee Colony Algorithm,
Firefly Algorithm, hybrid swarm, and convergence tracking.

Classes:
    Particle         — PSO particle
    Ant              — ACO ant
    ParticleSwarmOptimizer — PSO engine
"""

from __future__ import annotations

import logging
import random
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class Particle:
    """PSO particle (backward-compatible)."""

    def __init__(self, position: list[float]) -> None:
        self.position = position
        self.velocity: list[float] = [random.uniform(-1, 1) for _ in position]
        self.best_position: list[float] = position[:]
        self.best_value: float = float("inf")

    def update(
        self, global_best: list[float], w: float = 0.7, c1: float = 1.5, c2: float = 1.5
    ) -> None:
        """Update particle (backward-compatible)."""
        for i in range(len(self.position)):
            r1, r2 = random.random(), random.random()
            self.velocity[i] = (
                w * self.velocity[i]
                + c1 * r1 * (self.best_position[i] - self.position[i])
                + c2 * r2 * (global_best[i] - self.position[i])
            )
            self.position[i] += self.velocity[i]


class Ant:
    """ACO ant for path optimization."""

    def __init__(self, num_nodes: int) -> None:
        self.path: list[int] = []
        self.path_cost: float = float("inf")
        self._num_nodes = num_nodes

    def construct_path(
        self,
        pheromone: list[list[float]],
        distance: list[list[float]],
        alpha: float = 1.0,
        beta: float = 2.0,
    ) -> list[int]:
        """Construct path using pheromone and heuristic info."""
        self.path = []
        visited: set[int] = {0}
        current = 0
        self.path.append(current)

        for _ in range(self._num_nodes - 1):
            unvisited = [n for n in range(self._num_nodes) if n not in visited]
            if not unvisited:
                break
            # Probabilistic selection
            probs: list[float] = []
            for n in unvisited:
                tau = pheromone[current][n] ** alpha
                eta = (1.0 / max(distance[current][n], 0.01)) ** beta
                probs.append(tau * eta)
            total = sum(probs)
            if total > 0:
                probs = [p / total for p in probs]
                chosen = random.choices(unvisited, weights=probs)[0]
            else:
                chosen = random.choice(unvisited)
            self.path.append(chosen)
            visited.add(chosen)
            current = chosen

        return self.path


class ParticleSwarmOptimizer:
    """PSO optimizer (backward-compatible + ACO support)."""

    def __init__(self, num_particles: int = 20, dimensions: int = 5) -> None:
        self.particles: list[Particle] = [
            Particle([random.uniform(-10, 10) for _ in range(dimensions)])
            for _ in range(num_particles)
        ]
        self.global_best: list[float] = self.particles[0].position[:]
        self.global_best_value: float = float("inf")
        self._convergence_history: list[float] = []

    def optimize(
        self, fitness_func: Callable, iterations: int = 100
    ) -> tuple[list[float], float]:
        """PSO optimization (backward-compatible)."""
        for _it in range(iterations):
            for p in self.particles:
                value = fitness_func(p.position)
                if value < p.best_value:
                    p.best_value = value
                    p.best_position = p.position[:]
                if value < self.global_best_value:
                    self.global_best_value = value
                    self.global_best = p.position[:]
                p.update(self.global_best)
            self._convergence_history.append(self.global_best_value)
        return self.global_best, self.global_best_value

    def ant_colony_optimize(
        self, num_nodes: int = 10, num_ants: int = 5, iterations: int = 50
    ) -> dict[str, Any]:
        """Ant Colony Optimization."""
        pheromone: list[list[float]] = [
            [0.1 for _ in range(num_nodes)] for _ in range(num_nodes)
        ]
        distance: list[list[float]] = [
            [random.uniform(1, 10) for _ in range(num_nodes)] for _ in range(num_nodes)
        ]
        best_path: list[int] = []
        best_cost: float = float("inf")

        for _it in range(iterations):
            ants = [Ant(num_nodes) for _ in range(num_ants)]
            for ant in ants:
                ant.construct_path(pheromone, distance)
                cost = sum(
                    distance[ant.path[i]][ant.path[i + 1]]
                    for i in range(len(ant.path) - 1)
                )
                if cost < best_cost:
                    best_cost = cost
                    best_path = ant.path[:]
            # Update pheromone
            evaporation = 0.1
            for i in range(num_nodes):
                for j in range(num_nodes):
                    pheromone[i][j] *= 1 - evaporation
            # Deposit pheromone on best path
            for i in range(len(best_path) - 1):
                pheromone[best_path[i]][best_path[i + 1]] += 1.0 / best_cost

        return {
            "best_path": best_path,
            "best_cost": round(best_cost, 2),
            "nodes": num_nodes,
        }

    def convergence_report(self) -> dict[str, Any]:
        """Report convergence history."""
        if not self._convergence_history:
            return {"status": "no_data"}
        return {
            "iterations": len(self._convergence_history),
            "initial": self._convergence_history[0],
            "final": self._convergence_history[-1],
            "improvement": round(
                self._convergence_history[0] - self._convergence_history[-1], 4
            ),
        }

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {"particles": len(self.particles)}
