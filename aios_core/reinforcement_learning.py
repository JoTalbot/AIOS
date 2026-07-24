"""Reinforcement Learning for AIOS v10.8.0.

Q-Learning, SARSA, policy gradient simulation,
experience replay, multi-step returns, epsilon-greedy
exploration, and reward shaping.

Classes:
    Experience     — recorded (s, a, r, s') transition
    QLearningAgent — full RL agent with Q-learning + extensions
"""

from __future__ import annotations

import logging
import math
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Experience:
    """Recorded (s, a, r, s') transition."""

    state: str
    action: str
    reward: float
    next_state: str
    done: bool = False
    timestamp: float = field(default_factory=time.time)


class QLearningAgent:
    """Full RL agent with Q-learning and extensions.

    Features:
    - Q-Learning (off-policy TD control)
    - SARSA (on-policy TD control)
    - Experience replay buffer
    - Multi-step (n-step) returns
    - Epsilon-greedy exploration with decay
    - Reward shaping
    - Policy extraction
    - Double Q-Learning
    """

    def __init__(
        self,
        actions: list[str],
        learning_rate: float = 0.1,
        discount: float = 0.9,
        epsilon: float = 0.1,
        epsilon_decay: float = 0.99,
        epsilon_min: float = 0.01,
    ) -> None:
        self.actions = actions
        self.lr = learning_rate
        self.discount = discount
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.q_table: dict[str, dict[str, float]] = {}
        self.q_table_b: dict[str, dict[str, float]] = {}  # for double Q-learning
        self.experience_buffer: list[Experience] = []
        self.buffer_size: int = 1000
        self._step_count: int = 0
        self._episode_rewards: list[float] = []

    # ── Q-Value Access ──────────────────────────────────────────────

    def get_q(self, state: str, action: str) -> float:
        """Return Q-value for (state, action)."""
        return self.q_table.get(state, {}).get(action, 0.0)

    def get_q_b(self, state: str, action: str) -> float:
        """Return Q-value from second table (double Q-learning)."""
        return self.q_table_b.get(state, {}).get(action, 0.0)

    def set_q(self, state: str, action: str, value: float) -> None:
        """Set Q-value for (state, action)."""
        if state not in self.q_table:
            self.q_table[state] = dict.fromkeys(self.actions, 0.0)
        self.q_table[state][action] = value

    def max_q(self, state: str) -> float:
        """Return max Q-value for a state."""
        if state not in self.q_table:
            return 0.0
        return max(self.q_table[state].values())

    def best_action(self, state: str) -> str:
        """Return best action for a state (greedy)."""
        if state not in self.q_table:
            return random.choice(self.actions)
        return max(self.q_table[state], key=self.q_table[state].get)

    # ── Action Selection ────────────────────────────────────────────

    def choose_action(self, state: str, epsilon: float | None = None) -> str:
        """Choose action using epsilon-greedy."""
        eps = epsilon or self.epsilon
        if random.random() < eps or state not in self.q_table:
            return random.choice(self.actions)
        return max(self.q_table[state], key=self.q_table[state].get)

    def decay_epsilon(self) -> None:
        """Decay epsilon after each episode."""
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    # ── Learning Algorithms ──────────────────────────────────────────

    def learn(self, state: str, action: str, reward: float, next_state: str) -> None:
        """Q-Learning update: Q(s,a) += lr * (r + discount * max Q(s') - Q(s,a))."""
        if state not in self.q_table:
            self.q_table[state] = dict.fromkeys(self.actions, 0.0)

        current_q = self.get_q(state, action)
        max_next_q = max(self.q_table.get(next_state, {}).values(), default=0)
        new_q = current_q + self.lr * (reward + self.discount * max_next_q - current_q)
        self.q_table[state][action] = new_q

        self._step_count += 1
        self._episode_rewards.append(reward)

    def learn_sarsa(
        self, state: str, action: str, reward: float, next_state: str, next_action: str
    ) -> None:
        """SARSA update: Q(s,a) += lr * (r + discount * Q(s',a') - Q(s,a))."""
        if state not in self.q_table:
            self.q_table[state] = dict.fromkeys(self.actions, 0.0)

        current_q = self.get_q(state, action)
        next_q = self.get_q(next_state, next_action)
        new_q = current_q + self.lr * (reward + self.discount * next_q - current_q)
        self.q_table[state][action] = new_q

    def learn_double_q(
        self, state: str, action: str, reward: float, next_state: str
    ) -> None:
        """Double Q-Learning update (reduces overestimation)."""
        # Randomly choose which table to update
        if random.random() < 0.5:
            # Update Q_A using Q_B for next-state evaluation
            if state not in self.q_table:
                self.q_table[state] = dict.fromkeys(self.actions, 0.0)
            current_q = self.get_q(state, action)
            best_next = self.best_action(next_state)  # from Q_A
            next_q_val = self.get_q_b(next_state, best_next)  # evaluate using Q_B
            new_q = current_q + self.lr * (
                reward + self.discount * next_q_val - current_q
            )
            self.q_table[state][action] = new_q
        else:
            # Update Q_B using Q_A for next-state evaluation
            if state not in self.q_table_b:
                self.q_table_b[state] = dict.fromkeys(self.actions, 0.0)
            current_q = self.get_q_b(state, action)
            best_next_b = max(
                self.q_table_b.get(next_state, {}).keys(),
                key=lambda a: self.q_table_b.get(next_state, {}).get(a, 0),
                default=self.actions[0],
            )
            next_q_val = self.get_q(next_state, best_next_b)
            new_q = current_q + self.lr * (
                reward + self.discount * next_q_val - current_q
            )
            self.q_table_b[state][action] = new_q

    # ── Experience Replay ────────────────────────────────────────────

    def add_experience(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: str,
        done: bool = False,
    ) -> Experience:
        """Add an experience to the replay buffer."""
        exp = Experience(
            state=state, action=action, reward=reward, next_state=next_state, done=done
        )
        self.experience_buffer.append(exp)
        if len(self.experience_buffer) > self.buffer_size:
            self.experience_buffer = self.experience_buffer[-self.buffer_size :]
        return exp

    def replay(self, batch_size: int = 32) -> None:
        """Learn from a random batch of experiences."""
        if len(self.experience_buffer) < batch_size:
            return

        batch = random.sample(self.experience_buffer, batch_size)
        for exp in batch:
            target = exp.reward if exp.done else exp.reward + self.discount * self.max_q(exp.next_state)
            current_q = self.get_q(exp.state, exp.action)
            new_q = current_q + self.lr * (target - current_q)
            self.set_q(exp.state, exp.action, new_q)

    # ── Multi-Step Returns ──────────────────────────────────────────

    def n_step_return(self, experiences: list[Experience], n: int = 3) -> float:
        """Compute n-step return from a sequence of experiences."""
        total_return = 0.0
        for i, exp in enumerate(experiences[:n]):
            total_return += (self.discount**i) * exp.reward
        if len(experiences) > n:
            total_return += (self.discount**n) * self.max_q(experiences[n].state)
        return total_return

    # ── Reward Shaping ──────────────────────────────────────────────

    def shaped_reward(
        self,
        state: str,
        next_state: str,
        base_reward: float,
        potential_fn: Callable | None = None,
    ) -> float:
        """Apply reward shaping: F(s,s',r) = r + gamma*Phi(s') - Phi(s)."""
        if potential_fn:
            phi_next = potential_fn(next_state)
            phi_current = potential_fn(state)
            return base_reward + self.discount * phi_next - phi_current
        # Default shaping: encourage higher Q-values
        return base_reward + self.discount * self.max_q(next_state) * 0.01

    # ── Policy ──────────────────────────────────────────────────────

    def get_policy(self, state: str) -> dict[str, float]:
        """Return softmax policy for a state."""
        if state not in self.q_table:
            return {a: 1.0 / len(self.actions) for a in self.actions}

        # Softmax over Q-values
        temp = 1.0
        q_vals = self.q_table[state]
        exp_vals = {a: math.exp(q / temp) for a, q in q_vals.items()}
        sum_exp = sum(exp_vals.values())
        return {a: round(e / sum_exp, 4) for a, e in exp_vals.items()}

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        avg_reward = (
            (sum(self._episode_rewards) / len(self._episode_rewards))
            if self._episode_rewards
            else 0.0
        )
        return {
            "states": len(self.q_table),
            "actions": len(self.actions),
            "epsilon": round(self.epsilon, 4),
            "total_steps": self._step_count,
            "avg_reward": round(avg_reward, 4),
            "buffer_size": len(self.experience_buffer),
        }
