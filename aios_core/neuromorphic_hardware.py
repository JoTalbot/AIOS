"""Neuromorphic Hardware Abstraction for AIOS v10.9.0.

Neuromorphic chip simulation with spiking neuron
models, network mapping, power estimation, spike
routing, and STDP plasticity.

Classes:
    SpikingNeuron  — single leaky integrate-and-fire neuron
    NeuromorphicChip — full neuromorphic hardware engine
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SpikingNeuron:
    """Leaky Integrate-and-Fire (LIF) neuron."""

    id: str
    threshold: float = 1.0
    leak: float = 0.1  # leak factor per timestep
    membrane: float = 0.0  # membrane potential
    spikes: int = 0
    last_spike_time: float = 0.0

    def step(self, input_current: float, dt: float = 0.001) -> bool:
        """Execute one timestep. Returns True if neuron spiked."""
        # LIF dynamics: dV/dt = -leak * V + input
        self.membrane += dt * (-self.leak * self.membrane + input_current)

        if self.membrane >= self.threshold:
            self.membrane = 0.0  # reset after spike
            self.spikes += 1
            self.last_spike_time = time.time()
            return True
        return False


class NeuromorphicChip:
    """Full neuromorphic hardware engine.

    Features:
    - Network mapping to cores
    - Spiking neuron simulation (LIF)
    - Power estimation
    - Spike routing (simplified)
    - STDP (Spike-Timing Dependent Plasticity)
    - Event-driven processing
    """

    def __init__(self, cores: int = 128, neurons_per_core: int = 256) -> None:
        self.cores = cores
        self.neurons_per_core = neurons_per_core
        self.energy_per_spike = 0.000001  # pJ per spike
        self.neurons: dict[str, SpikingNeuron] = {}
        self.connections: dict[
            str, list[tuple[str, float]]
        ] = {}  # src → [(dst, weight)]
        self._spike_log: list[dict[str, Any]] = []
        self._power_total: float = 0.0
        self._total_spikes: int = 0

    # ── Network Mapping ──────────────────────────────────────────────

    def map_network(self, num_neurons: int) -> dict[str, Any]:
        """Map a network onto available cores."""
        cores_needed = (
            num_neurons + self.neurons_per_core - 1
        ) // self.neurons_per_core
        cores_used = min(cores_needed, self.cores)
        utilization = cores_used / self.cores

        return {
            "cores_used": cores_used,
            "cores_available": self.cores,
            "neurons_mapped": num_neurons,
            "neurons_per_core": self.neurons_per_core,
            "utilization": round(utilization, 4),
            "power_estimate_w": round(cores_used * 0.1, 4),
        }

    def add_neuron(
        self, neuron_id: str, threshold: float = 1.0, leak: float = 0.1
    ) -> SpikingNeuron:
        """Add a spiking neuron."""
        neuron = SpikingNeuron(id=neuron_id, threshold=threshold, leak=leak)
        self.neurons[neuron_id] = neuron
        return neuron

    def add_connection(self, src: str, dst: str, weight: float = 1.0) -> None:
        """Add a synaptic connection."""
        if src not in self.connections:
            self.connections[src] = []
        self.connections[src].append((dst, weight))

    # ── Simulation ──────────────────────────────────────────────────

    def simulate_step(
        self, inputs: dict[str, float], dt: float = 0.001
    ) -> dict[str, Any]:
        """Simulate one timestep across all neurons."""
        spike_events = []

        # Process input currents
        for neuron_id, input_current in inputs.items():
            neuron = self.neurons.get(neuron_id)
            if neuron and neuron.step(input_current, dt):
                spike_events.append(neuron_id)
                self._total_spikes += 1
                self._power_total += self.energy_per_spike

        # Propagate spikes through connections
        propagated_inputs = {}
        for src in spike_events:
            for dst, weight in self.connections.get(src, []):
                propagated_inputs[dst] = propagated_inputs.get(dst, 0.0) + weight

        # Apply STDP for connections where both pre and post fired
        for src in spike_events:
            for dst, _weight in self.connections.get(src, []):
                dst_neuron = self.neurons.get(dst)
                if dst_neuron and dst_neuron.spikes > 0:
                    # STDP: strengthen if pre before post
                    time_diff = time.time() - dst_neuron.last_spike_time
                    if time_diff < 0.01:  # recent post spike
                        delta_w = 0.01 * math.exp(-abs(time_diff) * 100)
                        # Update weight in connection list
                        self.connections[src] = [
                            (d, w + delta_w) if d == dst else (d, w)
                            for d, w in self.connections[src]
                        ]

        self._spike_log.append(
            {
                "spikes": spike_events,
                "propagated": propagated_inputs,
                "total_power": self._power_total,
            }
        )

        return {
            "spike_events": spike_events,
            "propagated_inputs": propagated_inputs,
            "total_spikes": self._total_spikes,
        }

    def simulate_sequence(
        self, input_sequence: list[dict[str, float]], dt: float = 0.001
    ) -> list[dict[str, Any]]:
        """Simulate a sequence of input steps."""
        results = []
        # Reset membrane potentials
        for neuron in self.neurons.values():
            neuron.membrane = 0.0

        for inputs in input_sequence:
            result = self.simulate_step(inputs, dt)
            results.append(result)
        return results

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        avg_spikes = self._total_spikes / len(self.neurons) if self.neurons else 0
        return {
            "cores": self.cores,
            "neurons_per_core": self.neurons_per_core,
            "neurons": len(self.neurons),
            "connections": sum(len(c) for c in self.connections.values()),
            "total_spikes": self._total_spikes,
            "avg_spikes_per_neuron": round(avg_spikes, 4),
            "energy_per_spike": self.energy_per_spike,
            "total_power": round(self._power_total, 8),
        }
