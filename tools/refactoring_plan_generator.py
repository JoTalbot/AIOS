"""Automated refactoring plan generator.

Builds a safe migration plan from dependency analysis results.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class RefactoringAction:
    module: str
    target_layer: str
    reason: str


@dataclass
class RefactoringPlan:
    actions: List[RefactoringAction] = field(default_factory=list)


class RefactoringPlanGenerator:
    """Converts dependency findings into ordered refactoring actions."""

    def generate(self, dependency_report: dict) -> RefactoringPlan:
        actions = []

        for module in dependency_report.get("hotspots", []):
            actions.append(
                RefactoringAction(
                    module=module,
                    target_layer="core",
                    reason="reduce coupling and isolate runtime logic",
                )
            )

        for cycle in dependency_report.get("cycles", []):
            actions.append(
                RefactoringAction(
                    module=" -> ".join(cycle),
                    target_layer="interfaces",
                    reason="break circular dependency",
                )
            )

        return RefactoringPlan(actions=actions)
