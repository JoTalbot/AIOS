"""Neural ODEs for AIOS"""

from typing import Callable, List


class NeuralODE:
    """Simplified Neural Ordinary Differential Equation solver."""

    def __init__(self, dynamics: Callable, solver: str = "euler"):
        self.dynamics = dynamics
        self.solver = solver

    def integrate(self, initial_state: List[float], t_span: tuple, steps: int = 100) -> List[List[float]]:
        t0, t1 = t_span
        dt = (t1 - t0) / steps
        trajectory = [initial_state[:]]
        state = initial_state[:]

        for _ in range(steps):
            if self.solver == "euler":
                dstate = self.dynamics(state)
                state = [s + dt * d for s, d in zip(state, dstate)]
            trajectory.append(state[:])

        return trajectory

    def stats(self) -> dict:
        return {"solver": self.solver}