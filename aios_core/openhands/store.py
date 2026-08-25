"""Персистентность контурного состояния (F7).

JSON-файл в octopus state dir (тот же каталог, что и ``agent_orchestrator_api``
через env ``OCTOPUS_ORCHESTRATOR_STATE_DIR``; без octopus — системный default).
Задачи сервиса переживают рестарт процесса. Секреты не хранятся.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from aios_core.orchestrator import Task, TaskStatus

from .models import Gate, ReviewDecision, TaskExtras

_STATE_NAME = "oh_contour_tasks"
_DEFAULT_DIR = Path(os.getenv("OH_CONTOUR_STATE_DIR", "/var/lib/aios/oh_contour"))


def _default_state_dir() -> Path:
    """State dir контура: octopus env приоритетнее, иначе OH_CONTOUR_STATE_DIR."""
    octopus = os.getenv("OCTOPUS_ORCHESTRATOR_STATE_DIR")
    return Path(octopus) if octopus else _DEFAULT_DIR


def extras_to_dict(extras: TaskExtras) -> dict:
    """Сериализация TaskExtras (frozenset/tuple/enum → JSON-типы)."""
    return {
        "task_id": extras.task_id,
        "branch": extras.branch,
        "workspace": extras.workspace,
        "required_capabilities": list(extras.required_capabilities),
        "dependencies": list(extras.dependencies),
        "required_gates": sorted(g.value for g in extras.required_gates),
        "passed_gates": sorted(g.value for g in extras.passed_gates),
        "conversation_ids": dict(extras.conversation_ids),
        "retry_count": extras.retry_count,
        "max_retries": extras.max_retries,
        "artifacts": list(extras.artifacts),
        "review_decision": extras.review_decision.value if extras.review_decision else None,
        "error": extras.error,
    }


def extras_from_dict(data: dict) -> TaskExtras:
    """Десериализация TaskExtras из JSON-формата ``extras_to_dict``."""
    decision = data.get("review_decision")
    return TaskExtras(
        task_id=data["task_id"],
        branch=data.get("branch", ""),
        workspace=data.get("workspace", ""),
        required_capabilities=tuple(data.get("required_capabilities", ())),
        dependencies=tuple(data.get("dependencies", ())),
        required_gates=frozenset(Gate(g) for g in data.get("required_gates", ("tests", "review"))),
        passed_gates=frozenset(Gate(g) for g in data.get("passed_gates", ())),
        conversation_ids=dict(data.get("conversation_ids", {})),
        retry_count=data.get("retry_count", 0),
        max_retries=data.get("max_retries", 3),
        artifacts=tuple(data.get("artifacts", ())),
        review_decision=ReviewDecision(decision) if decision else None,
        error=data.get("error"),
    )


def task_to_dict(task: Task) -> dict:
    """Минимальный сериализуемый срез канонической задачи контура."""
    return {
        "id": task.id,
        "name": task.name,
        "description": task.description,
        "status": str(task.status),
        "agent_id": task.agent_id,
        "created_at": task.created_at,
        "error": task.error,
    }


def task_from_dict(data: dict) -> Task:
    """Восстановить задачу из среза ``task_to_dict``."""
    task = Task(
        id=data["id"],
        name=data.get("name", ""),
        description=data.get("description", ""),
        agent_id=data.get("agent_id", "oh-orchestrator"),
    )
    try:
        task.status = TaskStatus(str(data.get("status", "pending")))
    except ValueError:
        task.status = TaskStatus.PENDING
    task.created_at = data.get("created_at", task.created_at)
    task.error = data.get("error")
    return task


class ContourStore:
    """JSON-хранилище контурных задач (одна запись = task + extras + result)."""

    def __init__(self, state_dir: Path | None = None) -> None:
        self._dir = Path(state_dir) if state_dir else _default_state_dir()

    def _path(self) -> Path:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            return self._dir / f"{_STATE_NAME}.json"
        except OSError:  # нет прав на системный dir (CI/sandbox) — repo-local fallback
            fallback = Path.cwd() / ".oh_contour"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback / f"{_STATE_NAME}.json"

    def _load_all(self) -> dict:
        path = self._path()
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                return {}
        return {}

    def _save_all(self, data: dict) -> None:
        self._path().write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def save(self, task: Task, extras: TaskExtras, contour_status: str | None = None) -> None:
        """Сохранить/обновить запись задачи."""
        data = self._load_all()
        data[extras.task_id] = {
            "task": task_to_dict(task),
            "extras": extras_to_dict(extras),
            "contour_status": contour_status,
        }
        self._save_all(data)

    def load(self, task_id: str) -> tuple[Task, TaskExtras, str | None] | None:
        """Загрузить (task, extras, contour_status) или None."""
        record = self._load_all().get(task_id)
        if record is None:
            return None
        return (
            task_from_dict(record["task"]),
            extras_from_dict(record["extras"]),
            record.get("contour_status"),
        )

    def load_all(self) -> dict[str, tuple[Task, TaskExtras, str | None]]:
        """Все записи (для восстановления сервиса после рестарта)."""
        return {tid: self.load(tid) for tid in self._load_all()}

    def list_ids(self) -> list[str]:
        """Идентификаторы всех сохранённых задач."""
        return list(self._load_all())
