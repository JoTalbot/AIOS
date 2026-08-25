"""Сервисный слой OpenHands-контура: входная точка для внешних систем.

Связывает каноническую ``orchestrator.Task`` с контурным lifecycle
(``OHOrchestrator`` + ``TaskExtras``), не меняя protected ``orchestrator.py``.
Хранилище MVP — in-memory; персистентность (octopus state / БД) — F7+.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aios_core.orchestrator import Task, TaskStatus

from .audit import OHAuditLogger
from .github import GitHubHelper
from .models import AgentRole, Gate, TaskExtras
from .runner import ConversationClient, OHOrchestrator, RunResult
from .store import ContourStore


@dataclass
class ContourTask:
    """Связка канонической задачи и контурных extras."""

    task: Task
    extras: TaskExtras
    result: RunResult | None = None


@dataclass
class ContourService:
    """Приём и исполнение задач OpenHands-контура.

    Args:
        client: Cloud-клиент (или совместимый по протоколу runner).
        github: GitHub-helper или None (тогда PR-стадия пропускается).
        audit: аудит-логгер контура.
        repository: ``owner/repo`` для Cloud-разговоров.
        base_branch: базовая ветка для diff/PR.
        store: персистентное хранилище; None — in-memory (по умолчанию
            создаётся ``ContourStore`` в octopus/state dir).
    """

    client: ConversationClient
    github: GitHubHelper | None = None
    audit: OHAuditLogger = field(default_factory=OHAuditLogger)
    repository: str | None = None
    base_branch: str = "main"
    store: ContourStore | None = None
    _tasks: dict[str, ContourTask] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.store is None:
            self.store = ContourStore()
        self._restore()

    def _restore(self) -> None:
        """Восстановить задачи из store (рестарт процесса)."""
        for task_id, record in self.store.load_all().items():
            if record is None:
                continue
            task, extras, contour_status = record
            result = None
            if contour_status is not None:
                result = RunResult(status=contour_status, extras=extras, error=extras.error)
            self._tasks[task_id] = ContourTask(task=task, extras=extras, result=result)

    def submit(
        self,
        title: str,
        description: str,
        *,
        required_gates: frozenset[Gate] | None = None,
        branch: str = "",
        max_retries: int = 3,
    ) -> str:
        """Принять задачу в контур. Возвращает task_id."""
        task = Task(name=title, description=description, agent_id="oh-orchestrator")
        extras = TaskExtras(task_id=task.id, branch=branch, max_retries=max_retries)
        if required_gates is not None:
            extras.required_gates = required_gates
        self._tasks[task.id] = ContourTask(task=task, extras=extras)
        self.store.save(task, extras)
        self.audit.log("task_submitted", task.id, AgentRole.ORCHESTRATOR, title=title)
        return task.id

    def run_task(self, task_id: str) -> RunResult:
        """Выполнить MVP-lifecycle принятой задачи и синхронизировать статус."""
        entry = self._tasks[task_id]
        orchestrator = OHOrchestrator(
            client=self.client,
            github=self.github,
            audit=self.audit,
            repository=self.repository,
            base_branch=self.base_branch,
        )
        result = orchestrator.run(task_id, entry.task.name, entry.task.description, entry.extras)
        entry.result = result
        entry.task.status = self._canonical_status(result.status)
        if result.error:
            entry.task.error = result.error
        self.store.save(entry.task, entry.extras, contour_status=result.status)
        return result

    def status(self, task_id: str) -> dict:
        """Сводный статус: каноническая задача + контурные поля."""
        entry = self._tasks.get(task_id)
        if entry is None:
            record = self.store.load(task_id)
            if record is None:
                raise KeyError(task_id)
            task, extras, contour_status = record
            entry = ContourTask(task=task, extras=extras)
            if contour_status is not None:
                entry.result = RunResult(status=contour_status, extras=extras, error=extras.error)
            self._tasks[task_id] = entry
        contour_status = entry.result.status if entry.result else TaskStatus.PENDING
        return {
            "task_id": task_id,
            "title": entry.task.name,
            "canonical_status": entry.task.status,
            "contour_status": contour_status,
            "retry_count": entry.extras.retry_count,
            "passed_gates": sorted(g.value for g in entry.extras.passed_gates),
            "review_decision": (
                entry.extras.review_decision.value if entry.extras.review_decision else None
            ),
            "artifacts": list(entry.extras.artifacts),
            "error": entry.extras.error,
        }

    @staticmethod
    def _canonical_status(contour_status: str) -> TaskStatus:
        """Проекция контурного статуса на канонический ``TaskStatus``."""
        mapping = {
            TaskStatus.COMPLETED: TaskStatus.COMPLETED,
            TaskStatus.CANCELLED: TaskStatus.CANCELLED,
            TaskStatus.FAILED: TaskStatus.FAILED,
        }
        return mapping.get(contour_status, TaskStatus.RUNNING)
