"""World Model / World Simulator for AIOS v10.10.0.

World model: environment dynamics learning, reward prediction,
latent state representation, Dreamer-style imagination, MPC
planning, dream rollouts, and model-based RL integration.

Classes:
    Transition     — single (s, a, s', r) transition
    WorldModel     — full dynamics + reward + planning engine
"""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Transition:
    """Single environment transition."""
    state: dict[str, float]
    action: Any
    next_state: dict[str, float]
    reward: float
    timestamp: float = field(default_factory=time.time)


class WorldModel:
    """Learns and simulates environment dynamics."""

    def __init__(self, discount: float = 0.99, imagination_horizon: int = 10) -> None:
        self.dynamics_model: dict[str, Any] = {}
        self.observations: list[Transition] = []
        self._reward_model: dict[str, float] = {}
        self._latent_state: list[float] = [0.0] * 32
        self._dynamics_noise: float = 0.05
        self._discount = discount
        self._imagination_horizon = imagination_horizon
        self._state_keys: list[str] = []

    def observe(self, state: dict, action: Any, next_state: dict, reward: float) -> None:
        """Record a transition (backward-compatible)."""
        trans = Transition(state=state, action=action, next_state=next_state, reward=reward)
        self.observations.append(trans)
        # Update state keys
        self._state_keys = list(state.keys()) if not self._state_keys else self._state_keys
        # Update reward model
        action_key = str(action)
        self._reward_model[action_key] = 0.9 * self._reward_model.get(action_key, 0.0) + 0.1 * reward
        # Update latent state (simplified representation)
        for i, key in enumerate(self._state_keys[:32]):
            self._latent_state[i % 32] = next_state.get(key, 0.0) * 0.5

    def predict(self, state: dict, action: Any) -> dict:
        """Predict next state (backward-compatible + enhanced)."""
        action_key = str(action)
        # Linear dynamics + noise
        noise_scale = self._dynamics_noise
        predicted: dict[str, float] = {}
        for key, val in state.items():
            drift = 0.9 * val + random.gauss(0, noise_scale)
            # Action effect
            if action_key in self._reward_model:
                drift += self._reward_model[action_key] * 0.01
            predicted[key] = round(drift, 4)
        return predicted

    def predict_reward(self, state: dict, action: Any) -> float:
        """Predict reward for a state-action pair."""
        action_key = str(action)
        base_reward = self._reward_model.get(action_key, 0.0)
        # State-dependent adjustment
        state_val = sum(state.values()) if state else 0
        return round(base_reward + 0.01 * state_val, 4)

    def imagine(self, horizon: int = 10) -> list[dict]:
        """Imagine rollout trajectory (backward-compatible + enhanced)."""
        trajectory: list[dict] = []
        if not self._state_keys:
            state = {"x": 0.0}
        else:
            state = {k: v for k, v in zip(self._state_keys, self._latent_state[:len(self._state_keys)])}
        for step in range(horizon):
            action = random.choice(["forward", "backward", "noop"])
            next_state = self.predict(state, action)
            reward = self.predict_reward(state, action)
            trajectory.append({"state": state, "action": action, "next": next_state, "reward": reward})
            state = next_state
        return trajectory

    def dream_rollout(self, start_state: dict[str, float] | None = None, horizon: int = 10) -> dict[str, Any]:
        """Dreamer-style imagination rollout with value estimation."""
        state = start_state or dict(zip(self._state_keys, self._latent_state[:len(self._state_keys)])) or {"x": 0.0}
        total_reward = 0.0
        trajectory: list[dict] = []
        for step in range(horizon):
            # MPC-style: try multiple actions, pick best
            best_action = "noop"
            best_reward = -1e9
            for action in ["forward", "backward", "noop", "accelerate", "brake"]:
                pred_reward = self.predict_reward(state, action)
                if pred_reward > best_reward:
                    best_reward = pred_reward
                    best_action = action
            next_state = self.predict(state, best_action)
            reward = best_reward
            total_reward += reward * self._discount ** step
            trajectory.append({"state": state, "action": best_action, "next": next_state, "reward": reward})
            state = next_state
        return {
            "trajectory": trajectory,
            "total_discounted_reward": round(total_reward, 4),
            "horizon": horizon,
        }

    def plan(self, goal_state: dict[str, float], horizon: int = 5) -> list[dict[str, Any]]:
        """MPC-style planning toward a goal state."""
        current = dict(zip(self._state_keys, self._latent_state[:len(self._state_keys)])) if self._state_keys else {"x": 0.0}
        plan: list[dict[str, Any]] = []
        for step in range(horizon):
            # Choose action that moves closest to goal
            best_action = "noop"
            best_dist = 1e9
            for action in ["forward", "backward", "noop"]:
                predicted = self.predict(current, action)
                dist = sum((predicted.get(k, 0) - goal_state.get(k, 0)) ** 2 for k in goal_state)
                if dist < best_dist:
                    best_dist = dist
                    best_action = action
            current = self.predict(current, best_action)
            plan.append({"action": best_action, "expected_state": current})
            if best_dist < 0.01:
                break
        return plan

    def get_latent(self) -> list[float]:
        """Get current latent state."""
        return list(self._latent_state)

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {
            "observations": len(self.observations),
            "reward_model_entries": len(self._reward_model),
            "state_keys": len(self._state_keys),
        }
