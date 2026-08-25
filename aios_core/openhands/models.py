"""Модели данных OpenHands-контура: роли, профили, права, расширения задачи.

Каноническая модель задачи — ``aios_core.orchestrator.Task``; здесь только
специфичные для контура дополнения (гейты, retry, артефакты), привязываемые
к задаче по ``task_id``.
"""

from dataclasses import dataclass, field
from enum import StrEnum

MAX_RETRIES = 3


class AgentRole(StrEnum):
    """Роли OpenHands-контура. MVP — первые пять, остальные подключаются как профили."""

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
    """Обязательные проверки, блокирующие переход задачи в COMPLETED."""

    TESTS = "tests"
    REVIEW = "review"
    SECURITY_REVIEW = "security_review"
    QA = "qa"


class ReviewDecision(StrEnum):
    """Решение независимого Reviewer."""

    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"


@dataclass
class AgentPermissions:
    """Права роли: read/write-области и пути, доступные для записи.

    ``allowed_paths`` — glob-паттерны относительно корня репозитория.
    ``deny_paths`` проверяется первым и имеет приоритет над ``allowed_paths``.
    Пустой ``allowed_paths`` означает запрет записи в файлы проекта.
    """

    read: str = "project"  # "project" | "all"
    write: str = "none"  # "none" | "orchestration" | "reports" | "workspace"
    allowed_paths: tuple[str, ...] = ()
    deny_paths: tuple[str, ...] = ()
    secret_allowlist: tuple[str, ...] = ()


@dataclass
class AgentProfile:
    """Профиль роли: права и привязки к существующим механизмам AIOS.

    ``registry_fields`` — дополнительные поля для записи в существующий
    octopus registry (``octopus_core/agent_orchestrator_api.py``).
    """

    role: AgentRole
    permissions: AgentPermissions
    memory_scope: str = "project"  # область памяти: autocoder_memory / experience pool
    registry_fields: dict = field(default_factory=dict)
    max_retries: int = MAX_RETRIES


@dataclass
class TaskExtras:
    """Контурные дополнения к ``orchestrator.Task`` (привязка по ``task_id``)."""

    task_id: str
    branch: str = ""
    workspace: str = ""
    required_capabilities: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()  # task_id блокирующих задач
    required_gates: frozenset[Gate] = frozenset({Gate.TESTS, Gate.REVIEW})
    passed_gates: frozenset[Gate] = frozenset()
    conversation_ids: dict = field(default_factory=dict)  # role -> conversation_id
    retry_count: int = 0
    max_retries: int = MAX_RETRIES
    artifacts: tuple[str, ...] = ()
    review_decision: ReviewDecision | None = None
    error: str | None = None

    def gates_satisfied(self) -> bool:
        """Все обязательные гейты пройдены."""
        return self.required_gates <= self.passed_gates

    def missing_gates(self) -> frozenset[Gate]:
        """Обязательные, но ещё не пройденные гейты."""
        return self.required_gates - self.passed_gates

    def can_retry(self) -> bool:
        """Не исчерпан ли лимит попыток (защита от бесконечных циклов)."""
        return self.retry_count < self.max_retries

    def register_retry(self) -> int:
        """Зарегистрировать новую попытку, вернуть текущий счётчик."""
        self.retry_count += 1
        return self.retry_count


@dataclass
class FailureReport:
    """Отчёт о финальном провале задачи (``TASK_FAILURE_REPORT.md`` в артефактах)."""

    task_id: str
    reason: str
    attempts: int
    last_error: str | None = None
    files_changed: tuple[str, ...] = ()
    suggested_next_step: str = ""
