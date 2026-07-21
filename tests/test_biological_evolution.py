"""Tests for Autonomous Bio-Inspired Genetic Evolution Engine (Horizon 6.0)."""

import pytest
from aios_core.biological_evolution import AgentGenome, BiologicalEvolutionEngine


def test_agent_genome_crossover_and_mutation():
    g1 = AgentGenome("g1", genes={"risk_aversion": 0.2, "reasoning_depth": 0.8})
    g2 = AgentGenome("g2", genes={"risk_aversion": 0.8, "reasoning_depth": 0.2})

    engine = BiologicalEvolutionEngine(population_size=6)
    child = engine.crossover(g1, g2, child_id="child_1")

    assert child.generation == 1
    assert "risk_aversion" in child.genes

    # Apply mutation
    old_val = child.genes["risk_aversion"]
    child.mutate(mutation_rate=1.0, mutation_scale=0.1)
    assert child.genes["risk_aversion"] != old_val or child.genes["risk_aversion"] in (0.01, 1.0)


def test_genetic_evolution_generation_stepping():
    engine = BiologicalEvolutionEngine(population_size=8, mutation_rate=0.2)

    # Evaluate fitness for population
    for g in engine.population:
        engine.evaluate_fitness(g, task_success_rate=0.9, latency_penalty=0.1, constitutional_violations=0)

    # Advance 2 generations
    gen1 = engine.step_generation()
    assert len(gen1) == 8
    assert engine.generation == 1

    for g in engine.population:
        engine.evaluate_fitness(g, task_success_rate=0.95, latency_penalty=0.05, constitutional_violations=0)

    gen2 = engine.step_generation()
    assert engine.generation == 2
    assert engine.stats()["best_fitness_latest"] > 0.0
