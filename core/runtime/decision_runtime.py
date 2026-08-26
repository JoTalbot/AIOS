"""Runtime integration layer for AIOS decisions."""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class RuntimeState:
    task_id: str
    status: str = "created"
    context: Dict[str, Any] = field(default_factory=dict)


class DecisionRuntime:
    """Connects runtime lifecycle with decision outputs."""

    def __init__(self, decision_engine):
        self.decision_engine = decision_engine

    def evaluate(self, state: RuntimeState, actions):
        context = {
            "task_id": state.task_id,
            "runtime_status": state.status,
            **state.context,
        }

        decision_context = {
            "state": context,
            "available_actions": actions,
        }

        return self.decision_engine.decide(decision_context)

    def transition(self, state: RuntimeState, decision):
        state.status = decision.action
        return state
