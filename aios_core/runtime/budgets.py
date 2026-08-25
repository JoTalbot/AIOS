"""Bounded action and runtime budgets for agents."""


class AgentBudget:
    """Fail-closed action budget with validated non-negative limits."""

    def __init__(self, max_actions: int = 100, max_runtime: float = 3600) -> None:
        if max_actions < 0 or max_runtime < 0:
            raise ValueError("budget limits must be non-negative")
        self.max_actions = max_actions
        self.max_runtime = max_runtime
        self.actions_used = 0

    @property
    def actions_remaining(self) -> int:
        """Return the number of actions that can still be consumed."""
        return max(0, self.max_actions - self.actions_used)

    def can_execute(self) -> bool:
        """Return whether one more action may be consumed."""
        return self.actions_remaining > 0

    def consume(self) -> None:
        """Consume one action or reject execution after exhaustion."""
        if not self.can_execute():
            raise RuntimeError("agent action budget exhausted")
        self.actions_used += 1
