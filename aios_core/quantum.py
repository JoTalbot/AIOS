"""Quantum-Inspired Algorithms for AIOS v11.0.0.

Quantum-inspired algorithms: QAOA simulation, variational
quantum eigensolver (VQE), quantum gates, circuit simulation,
measurement, entanglement detection, and annealing optimization.

Now includes true Quantum Error Mitigation (QEM) pipeline, featuring Zero-Noise Extrapolation
(ZNE) and Readout Error Mitigation.

Classes:
    QuantumGate      — single gate operation
    QuantumCircuit   — multi-gate circuit simulator
    QuantumInspiredOptimizer — annealing optimization
    QuantumErrorMitigation — QEM pipeline
"""

from __future__ import annotations

import logging
import math
import random
from collections.abc import Callable
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class QuantumGate:
    """Single quantum gate operation."""

    GATES = {
        "H": [
            [1 / math.sqrt(2), 1 / math.sqrt(2)],
            [1 / math.sqrt(2), -1 / math.sqrt(2)],
        ],
        "X": [[0, 1], [1, 0]],
        "Y": [[0, complex(0, -1)], [complex(0, 1), 0]],
        "Z": [[1, 0], [0, -1]],
        "S": [[1, 0], [0, complex(0, 1)]],
        "T": [[1, 0], [0, complex(math.cos(math.pi / 4), math.sin(math.pi / 4))]],
        "CNOT": "controlled-X",
        "RX": "parametric-rotation-x",
        "RY": "parametric-rotation-y",
        "RZ": "parametric-rotation-z",
    }

    def __init__(self, name: str, target: int = 0, param: float = 0.0) -> None:
        self.name = name
        self.target = target
        self.param = param
        self.matrix = self.GATES.get(name, [[1, 0], [0, 1]])

    def apply(self, state: List[complex]) -> List[complex]:
        """Apply gate to a 2-qubit state (simplified)."""
        if self.name == "H":
            s = 1 / math.sqrt(2)
            return [s * state[0] + s * state[1], s * state[0] - s * state[1]]
        elif self.name == "X":
            return [state[1], state[0]]
        elif self.name == "Z":
            return [state[0], -state[1]]
        elif self.name == "RY":
            cos_p = math.cos(self.param / 2)
            sin_p = math.sin(self.param / 2)
            return [
                cos_p * state[0] - sin_p * state[1],
                sin_p * state[0] + cos_p * state[1],
            ]
        elif self.name == "RX":
            cos_p = math.cos(self.param / 2)
            sin_p = math.sin(self.param / 2)
            return [
                cos_p * state[0] + complex(0, -sin_p) * state[1],
                complex(0, -sin_p) * state[0] + cos_p * state[1],
            ]
        return state

    def stats(self) -> Dict[str, Any]:
        return {"name": self.name, "target": self.target, "param": self.param}


class QuantumCircuit:
    """Multi-gate quantum circuit simulator with optional noise."""

    def __init__(self, qubits: int = 2, noise_factor: float = 0.0) -> None:
        self.qubits = qubits
        self.noise_factor = noise_factor
        self.gates: List[QuantumGate] = []
        self._state: List[complex] = [complex(1, 0)] + [complex(0, 0)] * (2**qubits - 1)
        self._measurement_results: List[int] = []

    def add_gate(self, name: str, target: int = 0, param: float = 0.0) -> QuantumGate:
        """Add a gate to the circuit."""
        gate = QuantumGate(name, target, param)
        self.gates.append(gate)
        return gate

    def simulate(self) -> List[complex]:
        """Simulate the circuit with depolarization noise."""
        state = [complex(1, 0), complex(0, 0)]  # |00>
        for gate in self.gates:
            state = gate.apply(state)
            
            # Apply depolarizing noise channel
            if self.noise_factor > 0:
                if random.random() < self.noise_factor:
                    # Randomize state slightly (depolarize)
                    state = [complex(random.random(), random.random()) for _ in state]
                    norm = math.sqrt(sum(abs(c)**2 for c in state))
                    state = [c/norm for c in state] if norm > 0 else state

        self._state = state
        return state

    def measure(self, shots: int = 1000) -> Dict[str, int]:
        """Measure circuit output with sampling and SPAM noise."""
        self.simulate()
        probs = [abs(s) ** 2 for s in self._state]
        total = sum(probs)
        if total == 0:
            return {"0": shots}
            
        probs_norm = [p / total for p in probs]
        counts: Dict[str, int] = {}
        for _ in range(shots):
            r = random.random()
            cumulative = 0.0
            for i, p in enumerate(probs_norm):
                cumulative += p
                if r <= cumulative:
                    # Apply Readout noise (SPAM)
                    if self.noise_factor > 0 and random.random() < self.noise_factor:
                        i = 1 - i  # bit flip
                    key = bin(i)[2:].zfill(self.qubits)
                    counts[key] = counts.get(key, 0) + 1
                    break
        return counts

    def entanglement_check(self) -> bool:
        """Check if state is entangled (simplified)."""
        self.simulate()
        if len(self._state) < 4:
            return False
        # Schmidt decomposition approximation
        state = self._state
        fidelity = abs(state[0]) ** 2 + abs(state[3]) ** 2
        return fidelity < 0.99 and fidelity > 0.01

    def qaoa_layer(
        self,
        cost_hamiltonian: Callable,
        mixer_angle: float = 0.5,
        cost_angle: float = 0.5,
    ) -> List[complex]:
        """Simulate a QAOA layer."""
        self.add_gate("H", 0)  # Initial superposition
        self.add_gate("RY", 0, cost_angle)  # Cost unitary
        self.add_gate("RX", 0, mixer_angle)  # Mixer unitary
        return self.simulate()

    def stats(self) -> Dict[str, Any]:
        return {
            "qubits": self.qubits,
            "gates": len(self.gates),
            "state_size": len(self._state),
            "noise_factor": self.noise_factor
        }


class QuantumErrorMitigation:
    """True Quantum Error Mitigation (QEM) pipeline for AIOS."""
    
    def __init__(self, base_noise: float = 0.05):
        self.base_noise = base_noise
        
    def zero_noise_extrapolation(self, circuit_builder: Callable[[float], QuantumCircuit], expectation_func: Callable[[Dict[str, int]], float], scale_factors: List[float] = [1.0, 2.0, 3.0]) -> float:
        """ZNE: Run circuit at amplified noise levels, then extrapolate back to zero noise."""
        results = []
        for scale in scale_factors:
            noise = self.base_noise * scale
            circ = circuit_builder(noise)
            counts = circ.measure(shots=2000)
            val = expectation_func(counts)
            results.append((scale, val))
            
        # Richardson Extrapolation (Linear fit for simplicity)
        # y = mx + c  => we want c (where x=0)
        x_sum = sum(x for x, y in results)
        y_sum = sum(y for x, y in results)
        xy_sum = sum(x*y for x, y in results)
        x2_sum = sum(x**2 for x, y in results)
        n = len(results)
        
        denominator = (n * x2_sum - x_sum**2)
        if denominator == 0:
            return results[0][1]
            
        m = (n * xy_sum - x_sum * y_sum) / denominator
        c = (y_sum - m * x_sum) / n
        
        return c

    def readout_error_mitigation(self, counts: Dict[str, int], confusion_matrix: List[List[float]]) -> Dict[str, float]:
        """Correct measurement distributions by inverting the confusion matrix (using Pseudo-inverse)."""
        # simplified 2-qubit (4 states) or 1-qubit (2 states) mapping
        # For our 2-state output:
        # C * P_true = P_measured => P_true = C^-1 * P_measured
        if len(confusion_matrix) == 2:
            det = confusion_matrix[0][0] * confusion_matrix[1][1] - confusion_matrix[0][1] * confusion_matrix[1][0]
            if det == 0:
                return {k: v/sum(counts.values()) for k, v in counts.items()}
                
            inv = [
                [confusion_matrix[1][1]/det, -confusion_matrix[0][1]/det],
                [-confusion_matrix[1][0]/det, confusion_matrix[0][0]/det]
            ]
            
            total = max(1, sum(counts.values()))
            p_meas = [counts.get("00", 0)/total, counts.get("01", 0)/total]
            
            p_true_0 = inv[0][0]*p_meas[0] + inv[0][1]*p_meas[1]
            p_true_1 = inv[1][0]*p_meas[0] + inv[1][1]*p_meas[1]
            
            # constrain
            p_true_0 = max(0.0, min(1.0, p_true_0))
            p_true_1 = max(0.0, min(1.0, p_true_1))
            norm = p_true_0 + p_true_1
            if norm > 0:
                p_true_0 /= norm
                p_true_1 /= norm
                
            return {"00": p_true_0, "01": p_true_1}
            
        return {k: v/sum(counts.values()) for k, v in counts.items()}


class QuantumInspiredOptimizer:
    """Quantum-inspired optimization (simulated annealing style)."""

    def __init__(self, temperature: float = 100.0) -> None:
        self.temperature = temperature

    def optimize(
        self, solution: List, cost_func: Callable, iterations: int = 1000
    ) -> Tuple[List, float]:
        """Quantum-inspired annealing."""
        current = solution[:]
        current_cost = cost_func(current)
        best = current[:]
        best_cost = current_cost

        for _i in range(iterations):
            neighbor = current[:]
            for _ in range(random.randint(1, 3)):
                if len(neighbor) > 1:
                    idx = random.randint(0, len(neighbor) - 1)
                    neighbor[idx] += random.gauss(0, self.temperature / 100)

            new_cost = cost_func(neighbor)
            if new_cost < best_cost:
                best = neighbor[:]
                best_cost = new_cost

            if new_cost < current_cost or random.random() < math.exp(
                -abs(new_cost - current_cost) / max(self.temperature, 1)
            ):
                current = neighbor[:]
                current_cost = new_cost

            self.temperature *= 0.995

        return best, best_cost

    def stats(self) -> Dict[str, Any]:
        return {"temperature": round(self.temperature, 2)}
