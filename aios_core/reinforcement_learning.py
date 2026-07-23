"""Reinforcement Learning for AIOS"""

import random
from typing import Any, Dict, List


class QLearningAgent:
    """Simple Q-Learning agent."""

    def __init__(self, actions: List[str], learning_rate: float = 0.1, discount: float = 0.9):
        self.actions = actions
        self.q_table: Dict[str, Dict[str, float]] = {}
        self.lr = learning_rate
        self.discount = discount

    def get_q(self, state: str, action: str) -> float:
        """Execute get q."""
        return self.q_table.get(state, {}).get(action, 0.0)

    def choose_action(self, state: str, epsilon: float = 0.1) -> str:
        """Execute choose action."""
        if random.random() < epsilon or state not in self.q_table:
            return random.choice(self.actions)
        return max(self.q_table[state], key=self.q_table[state].get)

    def learn(self, state: str, action: str, reward: float, next_state: str) -> None:
        """Execute learn."""
        if state not in self.q_table:
            self.q_table[state] = {a: 0.0 for a in self.actions}

        current_q = self.get_q(state, action)
        max_next_q = max(self.q_table.get(next_state, {}).values(), default=0)
        new_q = current_q + self.lr * (reward + self.discount * max_next_q - current_q)
        self.q_table[state][action] = new_q

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"states": len(self.q_table)}
