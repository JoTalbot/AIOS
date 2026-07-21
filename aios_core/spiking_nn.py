"""Spiking Neural Networks for AIOS"""

from typing import List


class SpikingNeuron:
    """Leaky Integrate-and-Fire neuron."""

    def __init__(self, threshold: float = 1.0, decay: float = 0.9):
        self.threshold = threshold
        self.decay = decay
        self.membrane = 0.0
        self.spikes = 0

    def step(self, input_current: float) -> int:
        self.membrane = self.membrane * self.decay + input_current
        if self.membrane >= self.threshold:
            self.spikes += 1
            self.membrane = 0.0
            return 1
        return 0


class SpikingLayer:
    """Spiking neural layer."""

    def __init__(self, size: int):
        self.neurons = [SpikingNeuron() for _ in range(size)]

    def forward(self, inputs: List[float], timesteps: int = 10) -> List[int]:
        outputs = [0] * len(self.neurons)
        for _ in range(timesteps):
            for i, neuron in enumerate(self.neurons):
                inp = inputs[i % len(inputs)] if inputs else 0
                spike = neuron.step(inp)
                outputs[i] += spike
        return outputs

    def stats(self) -> dict:
        return {"neurons": len(self.neurons)}