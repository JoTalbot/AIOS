"""Hierarchical Reinforcement Learning for AIOS"""

from typing import Dict, List


class Option:
    """Temporal abstraction (option) in HRL."""

    def __init__(self, name: str, initiation_set: List, policy, termination: float = 0.1):
        """Initialize Option."""
        self.name = name
        self.initiation_set = initiation_set
        self.policy = policy
        self.termination = termination


class HierarchicalRL:
    """Hierarchical Reinforcement Learning framework."""

    def __init__(self):
        """Initialize HierarchicalRL."""
        self.options: Dict[str, Option] = {}
        self.high_level_policy = {}

    def add_option(self, option: Option) -> None:
        """Execute add option."""
        self.options[option.name] = option

    def select_option(self, state: Dict) -> str:
        """Execute select option."""
        return list(self.options.keys())[0] if self.options else "default"

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"options": len(self.options)}
