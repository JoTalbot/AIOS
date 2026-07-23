"""Advanced Quantum-Inspired Optimization"""

import math
import random
from typing import Callable, List


class QuantumAnnealingOptimizer:
    """Simulated quantum annealing."""

    def __init__(self, initial_temp: float = 1000.0, cooling_rate: float = 0.95):
        self.temp = initial_temp
        self.cooling = cooling_rate

    def optimize(self, initial_solution: List, cost_func: Callable, iterations: int = 5000) -> None:
        current = initial_solution[:]
        best = current[:]
        best_cost = cost_func(best)

        for i in range(iterations):
            # Quantum-inspired perturbation
            neighbor = current[:]
            for _ in range(random.randint(1, 3)):
                if len(neighbor) > 1:
                    idx = random.randint(0, len(neighbor) - 1)
                    neighbor[idx] += random.gauss(0, self.temp / 100)

            new_cost = cost_func(neighbor)
            if new_cost < best_cost:
                best = neighbor[:]
                best_cost = new_cost

            # Accept with quantum probability
            if new_cost < cost_func(current) or random.random() < math.exp(
                -abs(new_cost - cost_func(current)) / self.temp
            ):
                current = neighbor[:]

            self.temp *= self.cooling

        return best, best_cost

    def stats(self) -> dict:
        return {"temperature": round(self.temp, 2)}
