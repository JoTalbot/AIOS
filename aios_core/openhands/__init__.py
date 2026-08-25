"""OpenHands-контур AIOS: оркестрация OpenHands-разговоров как специализированных агентов.

AIOS владеет оркестрацией, состоянием задач, правами и аудитом; OpenHands (Cloud API)
владеет исполнением в sandbox. Роли (Architect/Coder/Tester/Reviewer/...) — профили
разговоров, а не новые классы агентов. Подробнее: AIOS_OPENHANDS_INTEGRATION_PLAN.md.
"""

from .models import (
    MVP_ROLES,
    AgentPermissions,
    AgentProfile,
    AgentRole,
    FailureReport,
    Gate,
    ReviewDecision,
    TaskExtras,
)
from .state_machine import (
    TransitionError,
    allowed_transitions,
    can_transition,
    transition,
)

__all__ = [
    "MVP_ROLES",
    "AgentPermissions",
    "AgentProfile",
    "AgentRole",
    "FailureReport",
    "Gate",
    "ReviewDecision",
    "TaskExtras",
    "TransitionError",
    "allowed_transitions",
    "can_transition",
    "transition",
]
