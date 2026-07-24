"""Neural Architecture Search for AIOS v10.9.0.

NAS with random search, evolutionary search,
architecture evaluation, Pareto optimization,
search space management, and best architecture tracking.

Classes:
    Architecture   — candidate neural architecture
    NAS            — full NAS engine
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

SEARCH_SPACE = [
    "conv",
    "attention",
    "recurrent",
    "transformer",
    "pool",
    "dense",
    "dropout",
    "batch_norm",
]


@dataclass
class Architecture:
    """Candidate neural architecture."""

    id: str = ""
    layers: list[str] = field(default_factory=list)
    score: float = 0.0
    params: int = 0
    evaluated: bool = False
    created_at: float = field(default_factory=time.time)


class NAS:
    """Full Neural Architecture Search engine.

    Features:
    - Random architecture sampling
    - Architecture evaluation (simulated)
    - Evolutionary search (mutate + select)
    - Pareto optimization (accuracy vs size)
    - Search space management
    - Best architecture tracking
    """

    def __init__(self) -> None:
        self.architectures: dict[str, Architecture] = {}
        self.search_space: list[str] = list(SEARCH_SPACE)
        self._best: Architecture | None = None
        self._search_count: int = 0
        self._id_counter: int = 0

    def sample_architecture(self) -> list[str]:
        """Sample a random architecture (backward-compatible)."""
        num_layers = random.randint(3, 8)
        return [random.choice(self.search_space) for _ in range(num_layers)]

    def evaluate(self, arch: list[str]) -> float:
        """Evaluate an architecture (backward-compatible)."""
        # Simulated: more diverse layers = better, but too many = overfitting
        unique = len(set(arch))
        total = len(arch)
        # Score: balance diversity and size
        diversity_bonus = unique * 0.15
        size_penalty = total * 0.02 if total > 6 else 0
        base = sum(len(layer) for layer in arch) / 100
        score = base + diversity_bonus - size_penalty + random.uniform(0, 0.1)
        return round(max(0, score), 4)

    def create_architecture(self, layers: list[str]) -> Architecture:
        """Create and register an architecture."""
        self._id_counter += 1
        arch = Architecture(
            id=f"arch_{self._id_counter}",
            layers=layers,
            params=sum(random.randint(100, 5000) for _ in layers),
        )
        self.architectures[arch.id] = arch
        return arch

    def search(self, trials: int = 50) -> dict[str, Any]:
        """Run architecture search (backward-compatible)."""
        self._search_count += 1
        best_arch = None
        best_score = 0

        for _ in range(trials):
            layers = self.sample_architecture()
            score = self.evaluate(layers)
            arch = self.create_architecture(layers)
            arch.score = score
            arch.evaluated = True

            if score > best_score:
                best_score = score
                best_arch = arch

        if best_arch:
            self._best = best_arch

        return {
            "architecture": best_arch.layers if best_arch else None,
            "score": round(best_score, 4),
            "trials": trials,
            "arch_id": best_arch.id if best_arch else None,
        }

    def evolutionary_search(
        self, generations: int = 10, population: int = 20, mutation_rate: float = 0.3
    ) -> dict[str, Any]:
        """Evolutionary NAS: mutate + select best."""
        # Initialize population
        pop = []
        for _ in range(population):
            layers = self.sample_architecture()
            score = self.evaluate(layers)
            pop.append((layers, score))

        for _gen in range(generations):
            # Select top half
            pop.sort(key=lambda x: x[1], reverse=True)
            top = pop[: population // 2]

            # Mutate to create new population
            new_pop = list(top)
            for layers, _score in top:
                mutated = list(layers)
                for i in range(len(mutated)):
                    if random.random() < mutation_rate:
                        mutated[i] = random.choice(self.search_space)
                # Randomly add/remove layers
                if random.random() < 0.2 and len(mutated) < 8:
                    mutated.append(random.choice(self.search_space))
                if random.random() < 0.2 and len(mutated) > 3:
                    mutated.pop(random.randint(0, len(mutated) - 1))
                new_score = self.evaluate(mutated)
                new_pop.append((mutated, new_score))

            pop = new_pop

        best = max(pop, key=lambda x: x[1])
        best_arch = self.create_architecture(best[0])
        best_arch.score = best[1]
        best_arch.evaluated = True
        self._best = best_arch

        return {
            "architecture": best[0],
            "score": round(best[1], 4),
            "generations": generations,
        }

    def pareto_front(self) -> list[dict[str, Any]]:
        """Find Pareto-optimal architectures (accuracy vs params)."""
        evaluated = [a for a in self.architectures.values() if a.evaluated]
        if not evaluated:
            return []

        # Simple Pareto: find architectures where no other has both better score AND fewer params
        pareto = []
        for a in evaluated:
            dominated = any(
                other.score >= a.score and other.params <= a.params and other.id != a.id
                for other in evaluated
            )
            if not dominated:
                pareto.append(
                    {
                        "id": a.id,
                        "layers": a.layers,
                        "score": a.score,
                        "params": a.params,
                    }
                )

        return pareto

    def best(self) -> Architecture | None:
        """Return best architecture found."""
        return self._best

    def stats(self) -> dict[str, Any]:
        """Return summary statistics (backward-compatible)."""
        avg_score = (
            (
                sum(a.score for a in self.architectures.values())
                / len(self.architectures)
            )
            if self.architectures
            else 0
        )
        return {
            "architectures": len(self.architectures),
            "search_space": len(self.search_space),
            "searches": self._search_count,
            "avg_score": round(avg_score, 4),
            "best_score": self._best.score if self._best else 0,
        }
