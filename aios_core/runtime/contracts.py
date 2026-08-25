"""Common task/result contracts for AIOS agents."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class AgentTask:
    id: str
    goal: str
    task_type: str = "feature"
    priority: int = 50
    budget: int | None = None
    deadline_seconds: int | None = None
    permissions: tuple[str, ...] = ()
    context: dict[str, Any] = field(default_factory=dict)
    required_gates: tuple[str, ...] = ()


@dataclass(frozen=True)
class AgentResult:
    task_id: str
    status: AgentStatus
    output: str = ""
    evidence: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    cost: float = 0.0
    duration_seconds: float = 0.0
    verdict: str | None = None
