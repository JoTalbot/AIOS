"""Hierarchical Reinforcement Learning for AIOS v10.9.0.

Temporal abstraction (options) with initiation sets,
termination conditions, high-level policy, option
execution, goal decomposition, and HRL training.

Classes:
    Option         — temporal abstraction (skill)
    HierarchicalRL — full hierarchical RL engine
"""

from __future__ import annotations

import logging
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Option:
    """Temporal abstraction (option/skill) in HRL."""

    name: str
    initiation_set: list[str] = field(default_factory=list)
    policy: Callable | None = None
    termination: float = 0.1
    reward_total: float = 0.0
    executions: int = 0
    goal: str = ""
    sub_options: list[str] = field(default_factory=list)


class HierarchicalRL:
    """Full hierarchical RL engine.

    Features:
    - Option (skill) management with initiation/termination
    - High-level policy (option selection)
    - Goal decomposition into sub-options
    - Option execution with termination
    - Multi-level hierarchy
    - Training tracking
    """

    def __init__(self) -> None:
        self.options: dict[str, Option] = {}
        self.high_level_policy: dict[str, dict[str, float]] = {}
        self._execution_log: list[dict[str, Any]] = []
        self._goal_registry: dict[str, list[str]] = {}

    def add_option(
        self,
        option: Option | None = None,
        name: str = "",
        initiation_set: list[str] | None = None,
        termination: float = 0.1,
        goal: str = "",
        policy: Callable | None = None,
    ) -> Option:
        """Add an option/skill (backward-compatible)."""
        if option:
            self.options[option.name] = option
            return option
        opt = Option(
            name=name,
            initiation_set=initiation_set or [],
            policy=policy,
            termination=termination,
            goal=goal,
        )
        self.options[name] = opt
        return opt

    def remove_option(self, name: str) -> None:
        """Remove an option."""
        self.options.pop(name, None)

    def select_option(self, state: dict[str, Any] | str = "") -> str:
        """Select best option for current state (backward-compatible)."""
        state_str = str(state)

        # Check initiation sets
        eligible = []
        for name, option in self.options.items():
            if not option.initiation_set or any(
                s in state_str for s in option.initiation_set
            ):
                eligible.append(name)

        if not eligible:
            return list(self.options.keys())[0] if self.options else "default"

        # Use high-level policy weights
        policy = self.high_level_policy.get(state_str, {})
        if policy:
            best = max(eligible, key=lambda n: policy.get(n, 0.0))
            return best

        return eligible[0]

    def execute_option(self, option_name: str, steps: int = 10) -> dict[str, Any]:
        """Execute an option until termination."""
        option = self.options.get(option_name)
        if option is None:
            return {"completed": False, "reason": "option not found"}

        option.executions += 1
        reward = 0.0
        terminated = False

        for step in range(steps):
            # Check termination probability
            if random.random() < option.termination:
                terminated = True
                break
            # Simulate reward accumulation
            reward += random.uniform(0, 1)

        option.reward_total += reward

        self._execution_log.append(
            {
                "option": option_name,
                "steps": steps,
                "terminated": terminated,
                "reward": round(reward, 4),
            }
        )

        return {
            "option": option_name,
            "terminated": terminated,
            "reward": round(reward, 4),
            "steps": steps,
        }

    def decompose_goal(self, goal: str) -> list[str]:
        """Decompose a goal into sub-options."""
        if goal in self._goal_registry:
            return self._goal_registry[goal]

        # Auto-decompose: find options whose goals are related
        sub_options = []
        for name, option in self.options.items():
            if option.goal and (option.goal in goal or goal in option.goal):
                sub_options.append(name)

        if not sub_options:
            sub_options = list(self.options.keys())[:3]

        self._goal_registry[goal] = sub_options
        return sub_options

    def set_high_level_policy(
        self, state: str, option_weights: dict[str, float]
    ) -> None:
        """Set high-level policy weights for a state."""
        self.high_level_policy[state] = option_weights

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        avg_reward = (
            (sum(o.reward_total for o in self.options.values()) / len(self.options))
            if self.options
            else 0.0
        )
        return {
            "options": len(self.options),
            "executions": len(self._execution_log),
            "avg_reward": round(avg_reward, 4),
            "goals_registered": len(self._goal_registry),
        }
