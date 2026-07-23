"""Autonomous Bio-Inspired Genetic Evolution Engine for AIOS Horizon 6.0.

Provides Agent Genome chromosome encoding, Single-point & Uniform Crossover,
Gaussian Mutation, Constitutional Fitness Selection, and Natural Survival Selection across agent generations.
"""

import random
import time
from typing import Any, Dict, List, Optional, Tuple


class AgentGenome:
    """Agent Chromosome Gene Sequence encoding cognitive parameters and capabilities."""

    def __init__(self, genome_id: str, genes: Optional[Dict[str, float]] = None):
        self.genome_id = genome_id
        # Genes encode weights in range [0.0, 1.0]
        self.genes: Dict[str, float] = genes or {
            "risk_aversion": random.uniform(0.1, 0.9),
            "reasoning_depth": random.uniform(0.1, 0.9),
            "collaboration_weight": random.uniform(0.1, 0.9),
            "exploration_rate": random.uniform(0.1, 0.9),
            "memory_retention": random.uniform(0.1, 0.9),
        }
        self.fitness_score: float = 0.0
        self.generation: int = 0

    def mutate(self, mutation_rate: float = 0.1, mutation_scale: float = 0.05):
        """Apply Gaussian random mutation to gene sequences."""
        for key in self.genes:
            if random.random() < mutation_rate:
                delta = random.gauss(0, mutation_scale)
                self.genes[key] = min(1.0, max(0.01, self.genes[key] + delta))


class BiologicalEvolutionEngine:
    """Genetic Algorithm & Artificial Selection Engine for AIOS Agent Genomes."""

    def __init__(self, population_size: int = 10, mutation_rate: float = 0.15):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.generation = 0
        self.population: List[AgentGenome] = [
            AgentGenome(f"g_0_{i}") for i in range(population_size)
        ]
        self.history: List[Dict[str, Any]] = []

    def evaluate_fitness(
        self,
        genome: AgentGenome,
        task_success_rate: float,
        latency_penalty: float,
        constitutional_violations: int,
    ) -> float:
        """Calculate fitness incorporating performance speed, success rate, and constitutional compliance penalty."""
        base_fitness = (
            (task_success_rate * 0.5)
            + (genome.genes["reasoning_depth"] * 0.3)
            - (latency_penalty * 0.1)
        )

        # Constitutional Integrity Penalty: Any violation severely penalizes fitness score
        violation_penalty = constitutional_violations * 0.4
        final_fitness = max(0.001, round(base_fitness - violation_penalty, 4))

        genome.fitness_score = final_fitness
        return final_fitness

    def crossover(self, parent_a: AgentGenome, parent_b: AgentGenome, child_id: str) -> AgentGenome:
        """Perform Uniform Genetic Crossover between parent chromosomes."""
        child_genes = {}
        for key in parent_a.genes:
            child_genes[key] = parent_a.genes[key] if random.random() < 0.5 else parent_b.genes[key]

        child = AgentGenome(child_id, genes=child_genes)
        child.generation = max(parent_a.generation, parent_b.generation) + 1
        return child

    def step_generation(self) -> List[AgentGenome]:
        """Advance evolution by 1 generation using Natural Selection, Elitism, Crossover, and Mutation."""
        # 1. Sort population by fitness score descending
        self.population.sort(key=lambda g: g.fitness_score, reverse=True)

        new_pop: List[AgentGenome] = []

        # 2. Elitism: Preserve top 2 highest-performing constitutional genomes
        elite_count = min(2, len(self.population))
        for i in range(elite_count):
            elite = AgentGenome(
                f"g_{self.generation+1}_elite_{i}", genes=dict(self.population[i].genes)
            )
            elite.generation = self.generation + 1
            elite.fitness_score = self.population[i].fitness_score
            new_pop.append(elite)

        # 3. Fill remaining population via Crossover & Mutation
        gen_index = elite_count
        while len(new_pop) < self.population_size:
            p1, p2 = random.sample(self.population[: max(3, self.population_size // 2)], 2)
            child = self.crossover(p1, p2, child_id=f"g_{self.generation+1}_{gen_index}")
            child.mutate(mutation_rate=self.mutation_rate)
            new_pop.append(child)
            gen_index += 1

        self.generation += 1
        self.population = new_pop

        best_fitness = self.population[0].fitness_score
        mean_fitness = sum(g.fitness_score for g in self.population) / len(self.population)

        self.history.append(
            {
                "generation": self.generation,
                "best_fitness": round(best_fitness, 4),
                "mean_fitness": round(mean_fitness, 4),
                "timestamp": time.time(),
            }
        )

        return self.population

    def stats(self) -> Dict[str, Any]:
        return {
            "current_generation": self.generation,
            "population_size": len(self.population),
            "mutation_rate": self.mutation_rate,
            "best_fitness_latest": (self.population[0].fitness_score if self.population else 0.0),
        }
