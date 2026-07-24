"""Diffusion Models for AIOS v10.8.0.

Simplified diffusion probabilistic model with proper
noise schedule (linear/cosine), forward/reverse process,
DDPM/DDIM sampling, loss computation, and conditional
generation.

Classes:
    NoiseSchedule  — linear/cosine schedule management
    DiffusionModel — full diffusion model engine
"""

from __future__ import annotations

import logging
import math
import random
from typing import Any, Optional

logger = logging.getLogger(__name__)


class NoiseSchedule:
    """Noise schedule for diffusion models (linear or cosine)."""

    def __init__(self, timesteps: int = 1000, schedule_type: str = "linear",
                 beta_start: float = 0.0001, beta_end: float = 0.02) -> None:
        self.timesteps = timesteps
        self.schedule_type = schedule_type

        if schedule_type == "linear":
            self.betas = [beta_start + (beta_end - beta_start) * i / timesteps for i in range(timesteps)]
        elif schedule_type == "cosine":
            # Improved cosine schedule (Nichol & Dhariwal, 2021)
            self.betas = []
            for i in range(timesteps):
                t = i / timesteps
                alpha_bar_t = math.cos((t + 0.008) / 1.008 * math.pi / 2) ** 2
                alpha_bar_prev = math.cos(((i - 1) / timesteps + 0.008) / 1.008 * math.pi / 2) ** 2 if i > 0 else 1.0
                beta = 1 - alpha_bar_t / alpha_bar_prev
                self.betas.append(max(0.00001, min(0.999, beta)))
        else:
            self.betas = [beta_start + (beta_end - beta_start) * i / timesteps for i in range(timesteps)]

        # Compute alpha products
        self.alphas = [1 - b for b in self.betas]
        self.alpha_bars = []
        prod = 1.0
        for a in self.alphas:
            prod *= a
            self.alpha_bars.append(prod)

    def get_alpha_bar(self, t: int) -> float:
        """Return cumulative product of alphas at step t."""
        if t < 0:
            return 1.0
        return self.alpha_bars[min(t, self.timesteps - 1)]

    def get_beta(self, t: int) -> float:
        """Return beta at step t."""
        return self.betas[min(t, self.timesteps - 1)]


class DiffusionModel:
    """Full diffusion model engine.

    Features:
    - Linear/cosine noise schedule
    - Forward diffusion process
    - Reverse (denoising) process
    - DDPM sampling (full trajectory)
    - DDIM sampling (accelerated)
    - Loss computation (simple & weighted)
    - Conditional generation support
    """

    __slots__ = ('timesteps', 'schedule', 'schedule_type', 'betas', 'condition_fn')

    def __init__(self, timesteps: int = 1000, schedule_type: str = "linear",
                 beta_start: float = 0.0001, beta_end: float = 0.02,
                 condition_fn: Any = None) -> None:
        self.timesteps = timesteps
        self.schedule_type = schedule_type
        self.schedule = NoiseSchedule(timesteps, schedule_type, beta_start, beta_end)
        self.betas = self.schedule.betas
        self.condition_fn = condition_fn

    # ── Forward Process ─────────────────────────────────────────────

    def forward_process(self, x: list[float], t: int) -> list[float]:
        """Apply forward diffusion at timestep t to input x.

        q(x_t | x_0) = N(sqrt(alpha_bar_t) * x_0, (1-alpha_bar_t) * I)
        """
        noise = [random.gauss(0, 1) for _ in x]
        alpha_bar = self.schedule.get_alpha_bar(t)
        sqrt_alpha_bar = math.sqrt(alpha_bar)
        sqrt_one_minus_alpha_bar = math.sqrt(1 - alpha_bar)
        return [sqrt_alpha_bar * a + sqrt_one_minus_alpha_bar * n for a, n in zip(x, noise)]

    def forward_trajectory(self, x: list[float]) -> list[list[float]]:
        """Compute full forward trajectory from x_0 to pure noise."""
        trajectory = [x[:]]
        current = x[:]
        for t in range(self.timesteps):
            current = self.forward_process(current, t)
            trajectory.append(current[:])
        return trajectory

    # ── Reverse Process (Sampling) ──────────────────────────────────

    def reverse_step(self, x_t: list[float], t: int, predicted_noise: list[float]) -> list[float]:
        """Single reverse step: x_{t-1} from x_t and predicted noise."""
        alpha = self.schedule.alphas[t]
        alpha_bar = self.schedule.get_alpha_bar(t)
        beta = self.betas[t]

        # Predicted x_0
        sqrt_alpha_bar = math.sqrt(alpha_bar)
        sqrt_one_minus_alpha_bar = math.sqrt(1 - alpha_bar)
        predicted_x0 = [(xt - sqrt_one_minus_alpha_bar * pn) / sqrt_alpha_bar
                        for xt, pn in zip(x_t, predicted_noise)]

        # Direction to x_t
        sqrt_one_minus_alpha_bar_prev = math.sqrt(1 - self.schedule.get_alpha_bar(t - 1))
        sqrt_alpha_bar_prev = math.sqrt(self.schedule.get_alpha_bar(t - 1))
        direction_to_xt = [(sqrt_one_minus_alpha_bar_prev - sqrt_alpha_bar_prev * sqrt_one_minus_alpha_bar) / sqrt_one_minus_alpha_bar * pn
                          for pn in predicted_noise]

        # Combine
        sigma = math.sqrt(beta)
        noise = [random.gauss(0, sigma) for _ in x_t] if t > 0 else [0.0] * len(x_t)

        x_prev = [p + d + n for p, d, n in zip(predicted_x0, direction_to_xt, noise)]

        # Apply conditioning if available
        if self.condition_fn:
            x_prev = self.condition_fn(x_prev, t)

        return x_prev

    def sample_ddpm(self, shape: int, predicted_noise_fn: Any = None) -> list[float]:
        """DDPM sampling: full reverse trajectory (1000 steps).

        Uses predicted_noise_fn(x_t, t) to predict noise at each step.
        If None, uses a simple heuristic.
        """
        x = [random.gauss(0, 1) for _ in range(shape)]  # start from pure noise

        for t in reversed(range(self.timesteps)):
            if predicted_noise_fn:
                predicted_noise = predicted_noise_fn(x, t)
            else:
                # Simple heuristic: scale by sqrt(1 - alpha_bar)
                alpha_bar = self.schedule.get_alpha_bar(t)
                predicted_noise = [xt * (1 - math.sqrt(alpha_bar)) for xt in x]

            x = self.reverse_step(x, t, predicted_noise)

        return x

    def sample_ddim(self, shape: int, substeps: int = 50,
                    predicted_noise_fn: Any = None) -> list[float]:
        """DDIM sampling: accelerated reverse process with fewer steps."""
        x = [random.gauss(0, 1) for _ in range(shape)]

        # Create substep schedule
        step_ratio = self.timesteps // substeps
        sub_schedule = list(range(0, self.timesteps, step_ratio))

        for idx in reversed(range(len(sub_schedule))):
            t = sub_schedule[idx]
            t_prev = sub_schedule[idx - 1] if idx > 0 else 0

            if predicted_noise_fn:
                predicted_noise = predicted_noise_fn(x, t)
            else:
                alpha_bar = self.schedule.get_alpha_bar(t)
                predicted_noise = [xt * (1 - math.sqrt(alpha_bar)) for xt in x]

            # DDIM deterministic step (no noise)
            alpha_bar_t = self.schedule.get_alpha_bar(t)
            alpha_bar_prev = self.schedule.get_alpha_bar(t_prev)
            sqrt_alpha_bar = math.sqrt(alpha_bar_t)
            sqrt_alpha_bar_prev = math.sqrt(alpha_bar_prev)
            sqrt_one_minus_alpha_bar = math.sqrt(1 - alpha_bar_t)
            sqrt_one_minus_alpha_bar_prev = math.sqrt(1 - alpha_bar_prev)

            predicted_x0 = [(xt - sqrt_one_minus_alpha_bar * pn) / sqrt_alpha_bar
                           for xt, pn in zip(x, predicted_noise)]
            x = [sqrt_alpha_bar_prev * p + sqrt_one_minus_alpha_bar_prev * pn
                 for p, pn in zip(predicted_x0, predicted_noise)]

        return x

    def sample(self, shape: int) -> list[float]:
        """Generate shape random samples from the prior (backward-compatible)."""
        return [random.gauss(0, 1) for _ in range(shape)]

    # ── Loss Computation ────────────────────────────────────────────

    def compute_loss(self, x_0: list[float], predicted_noise: list[float],
                     t: int, weighted: bool = True) -> float:
        """Compute diffusion loss (MSE between predicted and actual noise)."""
        # Actual noise at step t
        alpha_bar = self.schedule.get_alpha_bar(t)
        sqrt_alpha_bar = math.sqrt(alpha_bar)
        sqrt_one_minus_alpha_bar = math.sqrt(1 - alpha_bar)

        # Actual noise (approximated from forward process)
        actual_noise = [(xt - sqrt_alpha_bar * x0) / sqrt_one_minus_alpha_bar
                       for xt, x0 in zip(self.forward_process(x_0, t), x_0)]

        # MSE
        mse = sum((a - p) ** 2 for a, p in zip(actual_noise, predicted_noise)) / len(actual_noise)

        if weighted:
            # SNR weighting
            snr = alpha_bar / (1 - alpha_bar)
            weight = min(snr, 5.0)
            mse *= weight

        return mse

    def compute_simple_loss(self, x_0: list[float], predicted_noise: list[float],
                            t: int) -> float:
        """Compute simple (unweighted) MSE loss."""
        return self.compute_loss(x_0, predicted_noise, t, weighted=False)

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "timesteps": self.timesteps,
            "schedule_type": self.schedule_type,
            "beta_start": self.betas[0],
            "beta_end": self.betas[-1],
            "alpha_bar_0": self.schedule.get_alpha_bar(0),
            "alpha_bar_final": self.schedule.get_alpha_bar(self.timesteps - 1),
        }
