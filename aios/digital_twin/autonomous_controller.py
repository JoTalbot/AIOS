"""Conservative controller for applying approved predictive actions."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class AutonomousController:
    approved_actions: List[str] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)

    def approve(self, action: str) -> None:
        if action not in self.approved_actions:
            self.approved_actions.append(action)

    def plan(self, action: str, parameters: Dict | None = None) -> Dict:
        if action not in self.approved_actions:
            raise PermissionError(f"Action not approved: {action}")
        plan = {"action": action, "parameters": parameters or {}}
        self.history.append(plan)
        return plan
