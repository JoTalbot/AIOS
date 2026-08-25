"""Task-aware GitHub Actions policies for OpenHands completion evidence."""
from __future__ import annotations

from dataclasses import dataclass

from .task_profiles import TaskType, classify_task


@dataclass(frozen=True)
class CIPolicy:
    task_type: TaskType
    required_workflows: tuple[str, ...]


DEFAULT_POLICY = CIPolicy(TaskType.UNKNOWN, ("AIOS Core Gate", "OpenHands Audit Integrity"))

POLICIES: dict[TaskType, CIPolicy] = {
    TaskType.BUGFIX: CIPolicy(TaskType.BUGFIX, ("AIOS Core Gate", "OpenHands Audit Integrity")),
    TaskType.FEATURE: CIPolicy(TaskType.FEATURE, ("AIOS Core Gate", "OpenHands Audit Integrity")),
    TaskType.REFACTOR: CIPolicy(TaskType.REFACTOR, ("AIOS Core Gate", "OpenHands Audit Integrity")),
    TaskType.SECURITY: CIPolicy(TaskType.SECURITY, ("AIOS Core Gate", "OpenHands Audit Integrity", "Supply Chain Gate", "Secret scanning")),
    TaskType.TEST: CIPolicy(TaskType.TEST, ("AIOS Core Gate", "OpenHands Audit Integrity")),
    TaskType.DOCUMENTATION: CIPolicy(TaskType.DOCUMENTATION, ("OpenHands Audit Integrity",)),
    TaskType.PERFORMANCE: CIPolicy(TaskType.PERFORMANCE, ("AIOS Core Gate", "OpenHands Audit Integrity")),
    TaskType.RESEARCH: CIPolicy(TaskType.RESEARCH, ("OpenHands Audit Integrity",)),
}


def policy_for(description: str) -> CIPolicy:
    return POLICIES.get(classify_task(description), DEFAULT_POLICY)
