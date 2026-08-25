"""Модели данных OpenHands-контура AIOS."""

from dataclasses import dataclass, field
from enum import StrEnum

MAX_RETRIES = 3
MAX_REPAIRS = 3


class AgentRole(StrEnum):
    ORCHESTRATOR = "orchestrator"
    ARCHITECT = "architect"
    CODER = "coder"
    TESTER = "tester"
    REVIEWER = "reviewer"
    SECURITY = "security"
    QA = "qa"
    DEVOPS = "devops"
    ANDROID = "android"
    ML = "ml"
    RESEARCH = "research"
    DOCUMENTATION = "documentation"


MVP_ROLES: tuple[AgentRole, ...] = (
    AgentRole.ORCHESTRATOR,
    AgentRole.ARCHITECT,
    AgentRole.CODER,
    AgentRole.TESTER,
    AgentRole.REVIEWER,
)


class Gate(StrEnum):
    TESTS = "tests"
    REVIEW = "review"
    SECURITY_REVIEW = "security_review"
    QA = "qa"


class ReviewDecision(StrEnum):
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"


@dataclass
class AgentPermissions:
    read: str = "project"
    write: str = "none"
    allowed_paths: tuple[str, ...] = ()
    deny_paths: tuple[str, ...] = ()
    secret_allowlist: tuple[str, ...] = ()


@dataclass
class AgentProfile:
    role: AgentRole
    permissions: AgentPermissions
    memory_scope: str = "project"
    registry_fields: dict = field(default_factory=dict)
    max_retries: int = MAX_RETRIES


@dataclass
class TaskExtras:
    task_id: str
    branch: str = ""
    workspace: str = ""
    required_capabilities: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    required_gates: frozenset[Gate] = frozenset({Gate.TESTS, Gate.REVIEW})
    passed_gates: frozenset[Gate] = frozenset()
    conversation_ids: dict = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = MAX_RETRIES
    repair_count: int = 0
    max_repairs: int = MAX_REPAIRS
    artifacts: tuple[str, ...] = ()
    review_decision: ReviewDecision | None = None
    error: str | None = None

    def gates_satisfied(self) -> bool:
        return self.required_gates <= self.passed_gates

    def missing_gates(self) -> frozenset[Gate]:
        return self.required_gates - self.passed_gates

    def mark_gate_passed(self, gate: Gate) -> None:
        """Record an explicitly approved gate without allowing arbitrary values."""
        if gate in self.required_gates:
            self.passed_gates = frozenset((*self.passed_gates, gate))

    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries

    def register_retry(self) -> int:
        self.retry_count += 1
        return self.retry_count

    def can_repair(self) -> bool:
        return self.repair_count < self.max_repairs

    def register_repair(self) -> int:
        self.repair_count += 1
        return self.repair_count


@dataclass
class FailureReport:
    task_id: str
    reason: str
    attempts: int
    last_error: str | None = None
    files_changed: tuple[str, ...] = ()
    suggested_next_step: str = ""
