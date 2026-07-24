"""Spiking Neural Networks for AIOS v10.10.0.

Spiking neural networks: leaky integrate-and-fire (LIF) neurons,
STDP learning rule, synaptic weight matrices, lateral inhibition,
Poisson spike encoding, multi-step simulation, and spike decoding.

Classes:
    SpikingNeuron  — LIF neuron with decay
    Synapse        — weighted connection with STDP
    SpikingLayer   — layer of LIF neurons with lateral inhibition
    SpikingNetwork — multi-layer spiking network
"""

from __future__ import annotations

import logging
import random
from typing import Any

logger = logging.getLogger(__name__)


class SpikingNeuron:
    """Leaky Integrate-and-Fire neuron."""

    def __init__(
        self, threshold: float = 1.0, decay: float = 0.9, resting: float = 0.0
    ) -> None:
        self.threshold = threshold
        self.decay = decay
        self.resting = resting
        self.membrane = resting
        self.spikes: int = 0
        self._spike_history: list[int] = []

    def step(self, input_current: float) -> int:
        """Single timestep (backward-compatible)."""
        self.membrane = self.membrane * self.decay + input_current
        if self.membrane >= self.threshold:
            self.spikes += 1
            self.membrane = self.resting
            self._spike_history.append(1)
            return 1
        self._spike_history.append(0)
        return 0

    def get_rate(self, window: int = 10) -> float:
        """Get recent firing rate."""
        recent = self._spike_history[-window:]
        return sum(recent) / len(recent) if recent else 0.0

    def reset(self) -> None:
        """Reset neuron state."""
        self.membrane = self.resting
        self.spikes = 0
        self._spike_history.clear()

    def stats(self) -> dict[str, Any]:
        return {
            "threshold": self.threshold,
            "decay": self.decay,
            "total_spikes": self.spikes,
        }


class Synapse:
    """Weighted connection with STDP plasticity."""

    def __init__(
        self, weight: float = 0.5, max_weight: float = 1.0, min_weight: float = 0.0
    ) -> None:
        self.weight = weight
        self.max_weight = max_weight
        self.min_weight = min_weight
        self._pre_spike_time: float = -1.0
        self._post_spike_time: float = -1.0

    def transmit(self, spike: int) -> float:
        """Transmit signal through synapse."""
        return self.weight * spike

    def stdp_update(
        self, pre_spiked: bool, post_spiked: bool, learning_rate: float = 0.01
    ) -> None:
        """STDP weight update: strengthen if pre→post, weaken if post→pre."""
        if pre_spiked and post_spiked:
            self.weight = min(self.max_weight, self.weight + learning_rate)
        elif post_spiked and not pre_spiked:
            self.weight = max(self.min_weight, self.weight - learning_rate * 0.5)

    def stats(self) -> dict[str, Any]:
        return {
            "weight": round(self.weight, 4),
            "range": f"{self.min_weight}-{self.max_weight}",
        }


class SpikingLayer:
    """Spiking neural layer with lateral inhibition."""

    def __init__(
        self,
        size: int,
        threshold: float = 1.0,
        decay: float = 0.9,
        inhibition: float = 0.1,
    ) -> None:
        self.neurons = [SpikingNeuron(threshold, decay) for _ in range(size)]
        self.inhibition = inhibition

    def forward(self, inputs: list[float], timesteps: int = 10) -> list[int]:
        """Multi-step forward pass (backward-compatible)."""
        outputs = [0] * len(self.neurons)
        for _ in range(timesteps):
            for i, neuron in enumerate(self.neurons):
                inp = inputs[i % len(inputs)] if inputs else 0
                # Lateral inhibition: subtract activity of neighbors
                lateral = (
                    sum(n.membrane for j, n in enumerate(self.neurons) if j != i)
                    * self.inhibition
                    / max(len(self.neurons) - 1, 1)
                )
                spike = neuron.step(inp - lateral)
                outputs[i] += spike
        return outputs

    def get_rates(self) -> list[float]:
        """Get firing rates for all neurons."""
        return [n.get_rate() for n in self.neurons]

    def reset(self) -> None:
        """Reset all neurons."""
        for n in self.neurons:
            n.reset()

    def stats(self) -> dict[str, Any]:
        return {"neurons": len(self.neurons), "inhibition": self.inhibition}


class SpikingNetwork:
    """Multi-layer spiking neural network."""

    def __init__(self, layer_sizes: list[int] | None = None) -> None:
        if layer_sizes is None:
            layer_sizes = [64, 32, 16]
        self.layers = [SpikingLayer(size) for size in layer_sizes]
        self._synapses: list[list[Synapse]] = []

    def connect_layers(
        self, idx_from: int, idx_to: int, initial_weight: float = 0.5
    ) -> None:
        """Create all-to-all synaptic connections between layers."""
        from_size = len(self.layers[idx_from].neurons)
        to_size = len(self.layers[idx_to].neurons)
        syn_matrix = [Synapse(initial_weight) for _ in range(from_size * to_size)]
        self._synapses.append(syn_matrix)

    def poisson_encode(
        self, values: list[float], duration: int = 10
    ) -> list[list[int]]:
        """Encode values as Poisson spike trains."""
        spike_trains: list[list[int]] = []
        for v in values:
            rate = max(0, min(1, v))
            train = [1 if random.random() < rate else 0 for _ in range(duration)]
            spike_trains.append(train)
        return spike_trains

    def forward(self, inputs: list[float], timesteps: int = 10) -> list[int]:
        """Forward pass through all layers."""
        current = inputs
        for layer in self.layers:
            current = layer.forward(current, timesteps)
        return current

    def decode_rates(self) -> list[float]:
        """Decode output layer firing rates."""
        if not self.layers:
            return []
        return self.layers[-1].get_rates()

    def stats(self) -> dict[str, Any]:
        return {
            "layers": len(self.layers),
            "layer_sizes": [l.stats()["neurons"] for l in self.layers],
            "synapse_groups": len(self._synapses),
        }
