"""Offline Reinforcement Learning for AIOS v10.8.0.

Offline RL from fixed datasets with BCQ/CQL algorithms,
behavior policy estimation, importance sampling,
OPE (Off-Policy Evaluation), conservative Q-learning,
and dataset management.

Classes:
    Transition     — offline dataset transition
    OfflineRLResult — training result
    OfflineRL      — full offline RL engine
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Transition:
    """Offline dataset transition (s, a, r, s', done)."""

    state: str
    action: str
    reward: float
    next_state: str
    done: bool = False
    behavior_prob: float = 1.0  # probability under behavior policy
    timestamp: float = field(default_factory=time.time)


@dataclass
class OfflineRLResult:
    """Offline RL training result."""

    algorithm: str
    dataset_size: int
    epochs: int
    estimated_value: float
    improvement_ratio: float
    cql_penalty: float = 0.0
    timestamp: float = field(default_factory=time.time)


class OfflineRL:
    """Full offline RL engine.

    Features:
    - Dataset management (add/query transitions)
    - Behavior policy estimation
    - Conservative Q-Learning (CQL) penalty
    - Batch-Constrained Q-learning (BCQ) filtering
    - Importance sampling weights
    - Off-Policy Evaluation (OPE)
    - Dataset statistics and quality metrics
    """

    def __init__(self, cql_alpha: float = 1.0, bcq_threshold: float = 0.3) -> None:
        self.dataset: list[Transition] = []
        self.q_values: dict[str, dict[str, float]] = {}  # state → {action: q}
        self.behavior_policy: dict[str, dict[str, float]] = {}  # state → {action: prob}
        self.cql_alpha = cql_alpha
        self.bcq_threshold = bcq_threshold
        self._training_history: list[OfflineRLResult] = []

    # ── Dataset Management ──────────────────────────────────────────

    def add_transition(self, transition: dict[str, Any] | Transition) -> Transition:
        """Add a transition to the offline dataset."""
        if isinstance(transition, dict):
            t = Transition(
                state=str(transition.get("state", "")),
                action=str(transition.get("action", "")),
                reward=float(transition.get("reward", 0)),
                next_state=str(transition.get("next_state", "")),
                done=bool(transition.get("done", False)),
                behavior_prob=float(transition.get("behavior_prob", 1.0)),
            )
        else:
            t = transition
        self.dataset.append(t)

        # Update behavior policy estimate
        self._update_behavior_policy(t.state, t.action)
        # Initialize Q-values
        if t.state not in self.q_values:
            self.q_values[t.state] = {}
        if t.action not in self.q_values[t.state]:
            self.q_values[t.state][t.action] = t.reward

        return t

    def add_batch(self, transitions: list[dict[str, Any]]) -> list[Transition]:
        """Add a batch of transitions."""
        return [self.add_transition(t) for t in transitions]

    def get_transitions(
        self, state: str | None = None, action: str | None = None, limit: int = 50
    ) -> list[Transition]:
        """Query transitions from the dataset."""
        result = self.dataset
        if state:
            result = [t for t in result if t.state == state]
        if action:
            result = [t for t in result if t.action == action]
        return result[-limit:]

    def dataset_stats(self) -> dict[str, Any]:
        """Return dataset statistics."""
        if not self.dataset:
            return {"size": 0}
        avg_reward = sum(t.reward for t in self.dataset) / len(self.dataset)
        unique_states = len(set(t.state for t in self.dataset))
        unique_actions = len(set(t.action for t in self.dataset))
        return {
            "size": len(self.dataset),
            "avg_reward": round(avg_reward, 4),
            "unique_states": unique_states,
            "unique_actions": unique_actions,
            "terminal_ratio": sum(1 for t in self.dataset if t.done)
            / len(self.dataset),
        }

    # ── Behavior Policy ────────────────────────────────────────────

    def _update_behavior_policy(self, state: str, action: str) -> None:
        """Update behavior policy estimate from new transition."""
        if state not in self.behavior_policy:
            self.behavior_policy[state] = {}
        self.behavior_policy[state][action] = (
            self.behavior_policy[state].get(action, 0) + 1
        )

    def estimate_behavior_prob(self, state: str, action: str) -> float:
        """Estimate probability of action under behavior policy."""
        state_policy = self.behavior_policy.get(state, {})
        total = sum(state_policy.values())
        if total == 0:
            return 1.0
        return state_policy.get(action, 0) / total

    # ── Training Algorithms ──────────────────────────────────────────

    def train(self, algorithm: str = "bcq", epochs: int = 100) -> OfflineRLResult:
        """Train an offline RL algorithm (backward-compatible)."""
        if algorithm == "bcq":
            result = self._train_bcq(epochs)
        elif algorithm == "cql":
            result = self._train_cql(epochs)
        else:
            result = OfflineRLResult(
                algorithm=algorithm,
                dataset_size=len(self.dataset),
                epochs=epochs,
                estimated_value=0.0,
                improvement_ratio=0.0,
            )

        self._training_history.append(result)
        return result

    def _train_bcq(self, epochs: int) -> OfflineRLResult:
        """Batch-Constrained Q-learning: only select actions likely under behavior policy."""
        avg_behavior_reward = 0.0
        for epoch in range(epochs):
            for t in self.dataset:
                # Only update Q for actions with sufficient behavior probability
                prob = self.estimate_behavior_prob(t.state, t.action)
                if prob >= self.bcq_threshold:
                    # Q-learning update
                    current_q = self.q_values.get(t.state, {}).get(t.action, 0.0)
                    max_next_q = max(
                        self.q_values.get(t.next_state, {}).values(), default=0
                    )
                    new_q = current_q + 0.1 * (t.reward + 0.9 * max_next_q - current_q)
                    if t.state not in self.q_values:
                        self.q_values[t.state] = {}
                    self.q_values[t.state][t.action] = new_q

        # Estimate policy value
        avg_q = sum(max(q.values()) for q in self.q_values.values() if q) / max(
            len(self.q_values), 1
        )
        avg_behavior_reward = sum(t.reward for t in self.dataset) / max(
            len(self.dataset), 1
        )

        improvement = (
            (avg_q - avg_behavior_reward) / abs(avg_behavior_reward)
            if avg_behavior_reward != 0
            else 0.0
        )

        return OfflineRLResult(
            algorithm="bcq",
            dataset_size=len(self.dataset),
            epochs=epochs,
            estimated_value=round(avg_q, 4),
            improvement_ratio=round(improvement, 4),
        )

    def _train_cql(self, epochs: int) -> OfflineRLResult:
        """Conservative Q-Learning: penalize actions not in dataset."""
        cql_penalty = 0.0
        for epoch in range(epochs):
            for t in self.dataset:
                # Standard Q-learning update
                current_q = self.q_values.get(t.state, {}).get(t.action, 0.0)
                max_next_q = max(
                    self.q_values.get(t.next_state, {}).values(), default=0
                )
                new_q = current_q + 0.1 * (t.reward + 0.9 * max_next_q - current_q)
                if t.state not in self.q_values:
                    self.q_values[t.state] = {}
                self.q_values[t.state][t.action] = new_q

            # CQL penalty: penalize Q-values for actions not in dataset
            for state, q_dict in self.q_values.items():
                # Find actions in dataset for this state
                dataset_actions = set(
                    t.action for t in self.dataset if t.state == state
                )
                for action in q_dict:
                    if action not in dataset_actions:
                        q_dict[action] -= self.cql_alpha * 0.1  # conservative penalty
                        cql_penalty += self.cql_alpha * 0.1

        avg_q = sum(max(q.values()) for q in self.q_values.values() if q) / max(
            len(self.q_values), 1
        )
        avg_behavior_reward = sum(t.reward for t in self.dataset) / max(
            len(self.dataset), 1
        )
        improvement = (
            (avg_q - avg_behavior_reward) / abs(avg_behavior_reward)
            if avg_behavior_reward != 0
            else 0.0
        )

        return OfflineRLResult(
            algorithm="cql",
            dataset_size=len(self.dataset),
            epochs=epochs,
            estimated_value=round(avg_q, 4),
            improvement_ratio=round(improvement, 4),
            cql_penalty=round(cql_penalty, 4),
        )

    # ── Importance Sampling ──────────────────────────────────────────

    def importance_weights(
        self, target_policy: dict[str, dict[str, float]]
    ) -> list[float]:
        """Compute importance sampling weights for OPE."""
        weights = []
        for t in self.dataset:
            behavior_prob = self.estimate_behavior_prob(t.state, t.action)
            target_prob = target_policy.get(t.state, {}).get(t.action, 0.01)
            weight = target_prob / behavior_prob if behavior_prob > 0 else 0.0
            weights.append(weight)
        return weights

    def off_policy_evaluation(
        self, target_policy: dict[str, dict[str, float]]
    ) -> float:
        """Off-Policy Evaluation using importance sampling (IS estimate)."""
        weights = self.importance_weights(target_policy)
        weighted_rewards = [w * t.reward for w, t in zip(weights, self.dataset)]

        # Normalized IS estimate (self-normalized)
        total_weights = sum(weights)
        if total_weights == 0:
            return 0.0
        return round(sum(weighted_rewards) / total_weights, 4)

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        avg_q = (
            (
                sum(max(q.values()) for q in self.q_values.values() if q)
                / max(len(self.q_values), 1)
            )
            if self.q_values
            else 0.0
        )
        return {
            "dataset_size": len(self.dataset),
            "states_learned": len(self.q_values),
            "avg_q_value": round(avg_q, 4),
            "cql_alpha": self.cql_alpha,
            "bcq_threshold": self.bcq_threshold,
            "training_runs": len(self._training_history),
        }
