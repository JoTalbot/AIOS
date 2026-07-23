"""Liquid Neural Networks for AIOS"""

from typing import List


class LiquidNeuron:
    """Simplified Liquid Time-Constant neuron."""

    def __init__(self, tau: float = 1.0):
        self.tau = tau
        self.state = 0.0

    def step(self, input_current: float, dt: float = 0.1) -> float:
        """Execute step."""
        self.state += dt * (-self.state / self.tau + input_current)
        return self.state


class LiquidNeuralNetwork:
    """Liquid Neural Network (LTC)."""

    def __init__(self, size: int = 64):
        self.neurons = [LiquidNeuron() for _ in range(size)]

    def forward(self, inputs: List[float], steps: int = 10) -> List[float]:
        """Execute forward."""
        outputs = []
        for _ in range(steps):
            for i, neuron in enumerate(self.neurons):
                inp = inputs[i % len(inputs)] if inputs else 0
                outputs.append(neuron.step(inp))
        return outputs

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"neurons": len(self.neurons)}
