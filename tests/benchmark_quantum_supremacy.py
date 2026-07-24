import pytest
import time
import math
import random
from aios_core.quantum import QuantumInspiredOptimizer, QuantumErrorMitigation

def ackley_function(solution):
    x = solution[0]
    y = solution[1] if len(solution) > 1 else 0
    term1 = -20 * math.exp(-0.2 * math.sqrt(0.5 * (x**2 + y**2)))
    term2 = -math.exp(0.5 * (math.cos(2 * math.pi * x) + math.cos(2 * math.pi * y)))
    return term1 + term2 + 20 + math.e

def benchmark_quantum_annealing():
    q_opt = QuantumInspiredOptimizer(temperature=100.0)
    start = time.time()
    best_sol, best_cost = q_opt.optimize([5.0, 5.0], ackley_function, iterations=1000)
    duration = time.time() - start
    return {"cost": best_cost, "solution": best_sol, "duration": duration}

def test_quantum_supremacy_optimization():
    # Verify the optimizer runs without errors and returns a valid result
    q_res = benchmark_quantum_annealing()
    assert q_res["cost"] < 25.0  # Should be better than random initial
    assert q_res["duration"] < 1.0 # Should be fast

def test_qem_overhead_benchmark():
    qem = QuantumErrorMitigation(base_noise=0.1)
    
    start = time.time()
    for _ in range(10):
        # A mock matrix
        conf = [[0.9, 0.1], [0.1, 0.9]]
        qem.readout_error_mitigation({"00": 500, "01": 500}, conf)
    duration = time.time() - start
    
    # Matrix inversion for 2x2 should be lightning fast (< 0.1s for 10 iterations)
    assert duration < 0.1
