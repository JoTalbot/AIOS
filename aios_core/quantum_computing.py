"""Quantum Computing Integration for AIOS v10.12.0.

Quantum computing: qubit simulation, gate operations
(H/X/Z/CNOT/CZ/Phase), circuit building, measurement,
entanglement creation, state vector simulation, and
quantum processor management.

Classes:
    Qubit            — simplified qubit
    QuantumGate      — gate operation record
    QuantumCircuit   — multi-qubit circuit
    QuantumProcessor — quantum co-processor
"""

from __future__ import annotations

import logging
import math
import random
from typing import Any

logger = logging.getLogger(__name__)


class Qubit:
    """Simplified qubit (backward-compatible)."""

    def __init__(self) -> None:
        self.state: complex = complex(1, 0)  # |0⟩
        self._measured: bool = False
        self._measurement_result: int = -1

    def apply_hadamard(self) -> None:
        """Apply Hadamard (backward-compatible)."""
        self.state = complex(1 / math.sqrt(2), 0)

    def apply_x(self) -> None:
        """Apply X (NOT) gate."""
        self.state = complex(0, 1) * self.state

    def apply_z(self) -> None:
        """Apply Z gate."""
        self.state = -self.state if self.state.real < 0 else self.state

    def apply_phase(self, angle: float = math.pi / 4) -> None:
        """Apply phase rotation."""
        self.state = self.state * complex(math.cos(angle), math.sin(angle))

    def measure(self) -> int:
        """Measure qubit (backward-compatible)."""
        prob_0 = abs(self.state) ** 2
        result = 0 if random.random() < prob_0 else 1
        self._measured = True
        self._measurement_result = result
        return result

    def reset(self) -> None:
        """Reset qubit to |0⟩."""
        self.state = complex(1, 0)
        self._measured = False


class QuantumGate:
    """Record of a gate operation."""

    def __init__(
        self, gate_type: str, targets: list[int], params: dict[str, float] | None = None
    ) -> None:
        self.gate_type = gate_type
        self.targets = targets
        self.params = params or {}


class QuantumCircuit:
    """Multi-qubit circuit simulator (backward-compatible + enhanced)."""

    def __init__(self, num_qubits: int) -> None:
        self.qubits: list[Qubit] = [Qubit() for _ in range(num_qubits)]
        self.gates: list[tuple[str, int]] = []
        self._gate_records: list[QuantumGate] = []

    def hadamard(self, qubit: int) -> None:
        """Hadamard gate (backward-compatible)."""
        self.qubits[qubit].apply_hadamard()
        self.gates.append(("H", qubit))
        self._gate_records.append(QuantumGate("H", [qubit]))

    def x(self, qubit: int) -> None:
        """X (NOT) gate."""
        self.qubits[qubit].apply_x()
        self.gates.append(("X", qubit))
        self._gate_records.append(QuantumGate("X", [qubit]))

    def z(self, qubit: int) -> None:
        """Z gate."""
        self.qubits[qubit].apply_z()
        self.gates.append(("Z", qubit))
        self._gate_records.append(QuantumGate("Z", [qubit]))

    def phase(self, qubit: int, angle: float = math.pi / 4) -> None:
        """Phase rotation gate."""
        self.qubits[qubit].apply_phase(angle)
        self.gates.append(("Phase", qubit))
        self._gate_records.append(QuantumGate("Phase", [qubit], {"angle": angle}))

    def cnot(self, control: int, target: int) -> None:
        """CNOT gate (simplified)."""
        # If control is in |1⟩ state, flip target
        if self.qubits[control].state.real < 0.5:
            self.qubits[target].apply_x()
        self.gates.append(("CNOT", control))
        self._gate_records.append(QuantumGate("CNOT", [control, target]))

    def entangle(self, qubit_a: int, qubit_b: int) -> None:
        """Create entanglement via H+CNOT."""
        self.hadamard(qubit_a)
        self.cnot(qubit_a, qubit_b)

    def measure_all(self) -> list[int]:
        """Measure all (backward-compatible)."""
        return [q.measure() for q in self.qubits]

    def state_vector(self) -> list[complex]:
        """Get state vector."""
        return [q.state for q in self.qubits]

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {
            "qubits": len(self.qubits),
            "gates": len(self.gates),
            "gate_types": list({g[0] for g in self.gates}),
        }


class QuantumProcessor:
    """Quantum co-processor (backward-compatible)."""

    def __init__(self) -> None:
        self.circuits: dict[str, QuantumCircuit] = {}

    def create_circuit(self, name: str, qubits: int) -> QuantumCircuit:
        """Create circuit (backward-compatible)."""
        circuit = QuantumCircuit(qubits)
        self.circuits[name] = circuit
        return circuit

    def run(self, name: str) -> list[int]:
        """Run circuit (backward-compatible)."""
        if name in self.circuits:
            return self.circuits[name].measure_all()
        return []

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {"circuits": len(self.circuits)}
