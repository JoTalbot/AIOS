"""OpenHands-контур AIOS: оркестрация OpenHands-разговоров как специализированных агентов.

AIOS владеет оркестрацией, состоянием задач, правами и аудитом; OpenHands (Cloud API)
владеет исполнением в sandbox. Роли (Architect/Coder/Tester/Reviewer/...) — профили
разговоров, а не новые классы агентов. Подробнее: AIOS_OPENHANDS_INTEGRATION_PLAN.md.
"""

from .client import OpenHandsClient, resolve_api_key
from .errors import (
    OpenHandsAPIError,
    OpenHandsAuthError,
    OpenHandsError,
    OpenHandsStartError,
    OpenHandsTimeoutError,
)
from .github import GitHubHelper, GitOperationError, GitRunner
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
from .permissions import PROFILES, check_paths, path_allowed, rbac_role_name, register_roles
from .profiles import build_prompt, conversation_title
from .runner import OHOrchestrator, RunResult
from .state_machine import (
    TransitionError,
    allowed_transitions,
    can_transition,
    transition,
)

__all__ = [
    "MVP_ROLES",
    "PROFILES",
    "AgentPermissions",
    "AgentProfile",
    "AgentRole",
    "FailureReport",
    "Gate",
    "GitHubHelper",
    "GitOperationError",
    "GitRunner",
    "OHOrchestrator",
    "OpenHandsAPIError",
    "OpenHandsAuthError",
    "OpenHandsClient",
    "OpenHandsError",
    "OpenHandsStartError",
    "OpenHandsTimeoutError",
    "ReviewDecision",
    "RunResult",
    "TaskExtras",
    "TransitionError",
    "allowed_transitions",
    "build_prompt",
    "can_transition",
    "check_paths",
    "conversation_title",
    "path_allowed",
    "rbac_role_name",
    "register_roles",
    "resolve_api_key",
    "transition",
]
