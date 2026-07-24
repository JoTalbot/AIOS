"""Liquid Neural Networks for AIOS v10.9.0.

Liquid Time-Constant (LTC) neural networks with
adaptive time constants, synaptic wiring, multi-step
simulation, and network architecture management.

Classes:
    LiquidNeuron        — single LTC neuron
    LiquidNeuralNetwork — full liquid neural network
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LiquidNeuron:
    """Liquid Time-Constant neuron with adaptive dynamics."""

    id: str = ""
    tau: float = 1.0  # time constant
    state: float = 0.0  # membrane potential
    sensitivity: float = 1.0  # input sensitivity
    spikes: int = 0
    last_update: float = 0.0

    def step(self, input_current: float, dt: float = 0.1) -> float:
        """Execute one timestep (backward-compatible)."""
        # LIF dynamics: dV/dt = (-V/tau + I*sensitivity)
        self.state += dt * (-self.state / self.tau + input_current * self.sensitivity)
        self.last_update = time.time()
        return self.state

    def adapt_tau(self, reward: float) -> None:
        """Adapt time constant based on reward signal."""
        self.tau = max(0.1, min(10.0, self.tau + reward * 0.1))


class LiquidNeuralNetwork:
    """Full Liquid Neural Network engine.

    Features:
    - LTC neuron simulation
    - Synaptic wiring (connections)
    - Multi-step forward pass
    - Adaptive time constants
    - Weight management
    """

    def __init__(self, size: int = 64) -> None:
        self.neurons: list[LiquidNeuron] = [
            LiquidNeuron(id=f"n{i}") for i in range(size)
        ]
        self.size = size
        self._connections: dict[str, list[tuple[str, float]]] = {}
        self._output_weights: list[float] = [0.1] * size
        self._trained: bool = False

    def add_connection(self, from_id: str, to_id: str, weight: float = 1.0) -> None:
        """Add a synaptic connection."""
        if from_id not in self._connections:
            self._connections[from_id] = []
        self._connections[from_id].append((to_id, weight))

    def forward(self, inputs: list[float], steps: int = 10) -> list[float]:
        """Multi-step forward pass (backward-compatible)."""
        outputs = []
        for _step in range(steps):
            for i, neuron in enumerate(self.neurons):
                inp = inputs[i % len(inputs)] if inputs else 0
                # Add connection inputs
                if neuron.id in self._connections:
                    for src_id, weight in self._connections[neuron.id]:
                        src_idx = int(src_id[1:]) if src_id.startswith("n") else 0
                        if src_idx < len(self.neurons):
                            inp += self.neurons[src_idx].state * weight
                neuron.step(inp)
                outputs.append(neuron.state)
        return outputs

    def adapt(self, reward: float) -> None:
        """Adapt all neurons based on reward."""
        for neuron in self.neurons:
            neuron.adapt_tau(reward)

    def set_weights(self, weights: list[float]) -> None:
        """Set output weights."""
        self._output_weights = weights[: self.size]

    def reset(self) -> None:
        """Reset all neuron states."""
        for neuron in self.neurons:
            neuron.state = 0.0

    def stats(self) -> dict[str, Any]:
        """Return summary statistics (backward-compatible)."""
        avg_state = sum(n.state for n in self.neurons) / len(self.neurons)
        return {
            "neurons": len(self.neurons),
            "connections": sum(len(c) for c in self._connections.values()),
            "avg_state": round(avg_state, 4),
            "trained": self._trained,
        }
