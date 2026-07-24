"""Neuromorphic Computing Abstraction for AIOS v10.10.0.

Neuromorphic computing: spiking neuron layers, crossbar
arrays, power estimation, event-driven processing, hardware
constraint modeling, and chip simulation.

Classes:
    SpikingNeuron     — LIF neuron model
    NeuromorphicLayer — event-driven layer
    CrossbarArray     — memristor crossbar simulation
    NeuromorphicChip  — full chip simulator
"""

from __future__ import annotations

import logging
import random
from typing import Any

logger = logging.getLogger(__name__)


class SpikingNeuron:
    """Simple spiking neuron model."""

    def __init__(self, threshold: float = 1.0, leak: float = 0.05) -> None:
        self.threshold = threshold
        self.leak = leak
        self.potential = 0.0
        self.spikes: int = 0
        self._last_spike_time: float = -1.0
        self._energy_consumed: float = 0.0

    def step(self, input_current: float, current_time: float = 0.0) -> int:
        """Single timestep with energy tracking (backward-compatible)."""
        self.potential += input_current - self.leak
        self._energy_consumed += abs(input_current) * 0.001  # pJ per spike event
        if self.potential >= self.threshold:
            self.spikes += 1
            self._last_spike_time = current_time
            self.potential = 0.0
            return 1
        if self.potential < 0:
            self.potential = 0.0
        return 0

    def reset(self) -> None:
        """Reset neuron state (backward-compatible)."""
        self.potential = 0.0
        self.spikes = 0
        self._last_spike_time = -1.0

    def stats(self) -> dict[str, Any]:
        return {
            "threshold": self.threshold,
            "spikes": self.spikes,
            "energy_pJ": round(self._energy_consumed, 4),
        }


class NeuromorphicLayer:
    """Event-driven neuromorphic layer."""

    def __init__(self, size: int, threshold: float = 1.0) -> None:
        self.neurons = [SpikingNeuron(threshold) for _ in range(size)]
        self._event_queue: list[
            tuple[float, int, float]
        ] = []  # (time, neuron_idx, current)

    def forward(self, inputs: list[float]) -> list[int]:
        """Forward pass (backward-compatible)."""
        outputs: list[int] = []
        for i, neuron in enumerate(self.neurons):
            inp = inputs[i % len(inputs)] if inputs else 0
            spike = neuron.step(inp)
            outputs.append(neuron.spikes)
        return outputs

    def inject_event(self, neuron_idx: int, current: float, time: float = 0.0) -> None:
        """Inject an event into the layer."""
        if 0 <= neuron_idx < len(self.neurons):
            self._event_queue.append((time, neuron_idx, current))

    def process_events(self) -> list[int]:
        """Process all queued events."""
        spikes: list[int] = [0] * len(self.neurons)
        for event_time, idx, current in self._event_queue:
            spike = self.neurons[idx].step(current, event_time)
            spikes[idx] += spike
        self._event_queue.clear()
        return spikes

    def total_energy(self) -> float:
        """Estimate total energy consumed by all neurons."""
        return sum(n._energy_consumed for n in self.neurons)

    def stats(self) -> dict[str, Any]:
        return {
            "neurons": len(self.neurons),
            "total_energy_pJ": round(self.total_energy(), 4),
        }


class CrossbarArray:
    """Memristor crossbar array simulation."""

    def __init__(self, rows: int = 64, cols: int = 64) -> None:
        self.rows = rows
        self.cols = cols
        # Initialize weight matrix (memristor conductances)
        self.weights: list[list[float]] = [
            [random.uniform(0.01, 0.99) for _ in range(cols)] for _ in range(rows)
        ]

    def read(self, row_idx: int, col_idx: int) -> float:
        """Read conductance at a crossbar point."""
        if 0 <= row_idx < self.rows and 0 <= col_idx < self.cols:
            return self.weights[row_idx][col_idx]
        return 0.0

    def write(self, row_idx: int, col_idx: int, value: float) -> None:
        """Write conductance at a crossbar point."""
        if 0 <= row_idx < self.rows and 0 <= col_idx < self.cols:
            self.weights[row_idx][col_idx] = max(0.01, min(0.99, value))

    def compute_vector_matrix(self, input_vector: list[float]) -> list[float]:
        """Compute vector × matrix on the crossbar."""
        result: list[float] = []
        for col in range(self.cols):
            total = 0.0
            for row in range(min(len(input_vector), self.rows)):
                total += input_vector[row] * self.weights[row][col]
            result.append(total)
        return result

    def estimate_power(self) -> float:
        """Estimate power consumption (µW)."""
        return self.rows * self.cols * 0.01  # ~0.01 µW per memristor

    def stats(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
            "cols": self.cols,
            "power_uW": round(self.estimate_power(), 2),
        }


class NeuromorphicChip:
    """Full neuromorphic chip simulator."""

    def __init__(self, name: str = "Loihi-Sim", cores: int = 128) -> None:
        self.name = name
        self.cores = cores
        self.layers: list[NeuromorphicLayer] = []
        self.crossbars: list[CrossbarArray] = []
        self._power_budget_mW = 500.0
        self._latency_ns = 0.0

    def add_layer(self, size: int, threshold: float = 1.0) -> NeuromorphicLayer:
        """Add a neuromorphic layer."""
        layer = NeuromorphicLayer(size, threshold)
        self.layers.append(layer)
        return layer

    def add_crossbar(self, rows: int = 64, cols: int = 64) -> CrossbarArray:
        """Add a crossbar array."""
        crossbar = CrossbarArray(rows, cols)
        self.crossbars.append(crossbar)
        return crossbar

    def simulate(self, inputs: list[float], timesteps: int = 10) -> dict[str, Any]:
        """Simulate chip execution for multiple timesteps."""
        all_spikes: list[list[int]] = []
        for t in range(timesteps):
            current_input = inputs
            for layer in self.layers:
                spikes = layer.forward(current_input)
                all_spikes.append(spikes)
                current_input = [s * 0.1 for s in spikes]
        self._latency_ns = (
            timesteps * len(self.layers) * 100
        )  # ~100ns per layer per timestep
        return {
            "spikes": all_spikes,
            "timesteps": timesteps,
            "total_spikes": sum(sum(s) for s in all_spikes),
            "latency_ns": self._latency_ns,
        }

    def power_report(self) -> dict[str, Any]:
        """Generate power consumption report."""
        neuron_power = (
            sum(layer.total_energy() for layer in self.layers) * 1e6
        )  # convert pJ to mW equivalent
        crossbar_power = (
            sum(cb.estimate_power() for cb in self.crossbars) / 1000
        )  # µW → mW
        return {
            "chip": self.name,
            "neuron_power_mW": round(neuron_power, 2),
            "crossbar_power_mW": round(crossbar_power, 2),
            "budget_mW": self._power_budget_mW,
            "within_budget": (neuron_power + crossbar_power) <= self._power_budget_mW,
        }

    def stats(self) -> dict[str, Any]:
        return {
            "chip": self.name,
            "cores": self.cores,
            "layers": len(self.layers),
            "crossbars": len(self.crossbars),
        }
