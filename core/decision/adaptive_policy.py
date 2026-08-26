from typing import Any


class AdaptiveDecisionPolicy:
    """Combines decision context with learned recovery experience."""

    def __init__(self, memory: Any = None):
        self.memory = memory

    def enrich(self, context: dict) -> dict:
        if self.memory is None:
            return context

        action = context.get("action")
        if action:
            context["memory_score"] = self.memory.score_action(action)

        return context

    def choose_action(self, context: dict) -> str:
        if context.get("memory_score", 0) > 0:
            return context.get("action", "continue")

        return context.get("fallback", "continue")
