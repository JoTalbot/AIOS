"""Neuromorphic Spiking Neural Network (SNN) Matrix Engine for AIOS Horizon 6.0.

Provides event-driven Leaky Integrate-and-Fire (LIF) spiking neuron arrays,
membrane potential dynamics, STDP unsupervised synaptic plasticity, and
sub-millisecond neuromorphic event routing.
"""

import math
import time
from typing import Dict, List, Optional, Any, Tuple


class LIFNeuron:
    """Leaky Integrate-and-Fire (LIF) Spiking Neuron model."""

    def __init__(self, neuron_id: str, v_threshold: float = 1.0, v_rest: float = 0.0, tau: float = 10.0):
        self.neuron_id = neuron_id
        self.v_threshold = v_threshold
        self.v_rest = v_rest
        self.v_membrane = v_rest
        self.tau = tau  # Membrane decay time constant
        self.last_spike_time: Optional[float] = None
        self.spike_count = 0

    def integrate_current(self, current: float, dt_ms: float = 1.0) -> bool:
        """Integrate input current into membrane potential with exponential leak decay."""
        decay = math.exp(-dt_ms / self.tau)
        self.v_membrane = self.v_rest + (self.v_membrane - self.v_rest) * decay + current

        # Check threshold spike condition
        if self.v_membrane >= self.v_threshold:
            self.v_membrane = self.v_rest  # Reset
            self.last_spike_time = time.time()
            self.spike_count += 1
            return True  # Spike fired!

        return False


class NeuromorphicMatrixEngine:
    """Spiking Neural Network Matrix Engine with STDP learning."""

    def __init__(self, size: int = 16):
        self.size = size
        self.neurons: List[LIFNeuron] = [LIFNeuron(f"sn_{i}") for i in range(size)]
        self.synaptic_weights: Dict[Tuple[int, int], float] = {}

        # Initialize default random or uniform synaptic connections
        for i in range(size):
            for j in range(size):
                if i != j:
                    self.synaptic_weights[(i, j)] = 0.25

    def step_simulation(self, input_currents: Dict[int, float], dt_ms: float = 1.0) -> List[int]:
        """Simulate one discrete time step dt across all neurons, returning indices of fired neurons."""
        spiked_neurons = []

        # 1. Integrate external currents + synaptic inputs
        for i, neuron in enumerate(self.neurons):
            current = input_currents.get(i, 0.0)

            # Accumulate weight-driven synaptic currents from previously fired connections
            for (pre, post), w in self.synaptic_weights.items():
                if post == i and self.neurons[pre].last_spike_time is not None:
                    # Small decaying input current contribution
                    if time.time() - self.neurons[pre].last_spike_time < 0.05:
                        current += w * 0.5

            if neuron.integrate_current(current, dt_ms=dt_ms):
                spiked_neurons.append(i)

        # 2. Spike-Timing-Dependent Plasticity (STDP) Synaptic Weight Adjustment
        self._apply_stdp_plasticity(spiked_neurons)

        return spiked_neurons

    def _apply_stdp_plasticity(self, spiked_indices: List[int]):
        """Adjust synaptic weights based on temporal spike correlation."""
        for post_idx in spiked_indices:
            for pre_idx in range(self.size):
                if pre_idx == post_idx:
                    continue
                pair = (pre_idx, post_idx)
                pre_neuron = self.neurons[pre_idx]

                if pre_neuron.last_spike_time is not None:
                    delta_t = time.time() - pre_neuron.last_spike_time
                    if delta_t > 0 and delta_t < 0.1:
                        # Potentiation: Pre before Post -> strengthen synapse
                        self.synaptic_weights[pair] = min(1.0, self.synaptic_weights[pair] + 0.02)
                    elif delta_t < 0:
                        # Depression: Post before Pre -> weaken synapse
                        self.synaptic_weights[pair] = max(0.01, self.synaptic_weights[pair] - 0.01)

    def stats(self) -> Dict[str, Any]:
        total_spikes = sum(n.spike_count for n in self.neurons)
        return {
            "matrix_size": self.size,
            "total_synapses": len(self.synaptic_weights),
            "total_spikes_fired": total_spikes,
            "mean_synaptic_weight": round(sum(self.synaptic_weights.values()) / len(self.synaptic_weights), 4)
        }
