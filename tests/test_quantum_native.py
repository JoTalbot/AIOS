"""Tests for Quantum Native Computing & QAOA Simulator (Horizon 5.0)."""

import pytest
from aios_core.quantum_native import QuantumCircuitSimulator, QuantumNativeEngine


def test_quantum_circuit_simulator_hadamard_and_cnot():
    sim = QuantumCircuitSimulator(num_qubits=2)

    # State initially |00> with 100% probability
    probs_init = sim.measure_probabilities()
    assert round(probs_init[0], 2) == 1.0

    # Apply Hadamard on qubit 0 -> creates equal superposition (|00> + |01>) / sqrt(2)
    sim.apply_hadamard(qubit_index=0)
    probs_super = sim.measure_probabilities()
    assert round(probs_super[0], 2) == 0.5
    assert round(probs_super[1], 2) == 0.5

    # Apply CNOT with control=0, target=1 -> creates Bell State (|00> + |11>) / sqrt(2)
    sim.apply_cnot(control_qubit=0, target_qubit=1)
    probs_bell = sim.measure_probabilities()
    assert round(probs_bell[0], 2) == 0.5
    assert round(probs_bell[3], 2) == 0.5


def test_quantum_native_engine_qaoa_optimization():
    engine = QuantumNativeEngine()
    sample_tasks = [
        {"id": "t1", "action": "scrape_data"},
        {"id": "t2", "action": "analyze_sentiment"},
        {"id": "t3", "action": "generate_report"},
    ]

    res = engine.optimize_task_schedule_qaoa(tasks=sample_tasks, num_agents=2)
    assert "optimal_schedule" in res
    assert len(res["optimal_schedule"]) == 3
    assert res["qubits_used"] == 3
    assert engine.stats()["circuits_executed"] == 1
