"""AIOS v20 intent engine.

Transforms external goals into normalized execution intents.
"""

from dataclasses import dataclass, field


@dataclass
class Intent:
    goal: str
    context: dict = field(default_factory=dict)


class IntentEngine:
    def create(self, goal: str, context: dict | None = None) -> Intent:
        return Intent(goal=goal, context=context or {})
