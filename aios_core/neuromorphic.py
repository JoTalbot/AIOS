"""Neuromorphic Computing Abstraction for AIOS"""

from typing import Dict, List


class SpikingNeuron:
    """Simple spiking neuron model."""

    def __init__(self, threshold: float = 1.0):
        self.threshold = threshold
        self.potential = 0.0
        self.spikes = 0

    def step(self, input_current: float) -> None:
        self.potential += input_current
        if self.potential >= self.threshold:
            self.spikes += 1
            self.potential = 0.0

    def reset(self) -> None:
        self.potential = 0.0
        self.spikes = 0


class NeuromorphicLayer:
    """Simple neuromorphic layer."""

    def __init__(self, size: int):
        self.neurons = [SpikingNeuron() for _ in range(size)]

    def forward(self, inputs: List[float]) -> List[int]:
        outputs = []
        for i, neuron in enumerate(self.neurons):
            neuron.step(inputs[i % len(inputs)] if inputs else 0)
            outputs.append(neuron.spikes)
        return outputs

    def stats(self) -> dict:
        return {"neurons": len(self.neurons)}
