"""Typed execution results used across the AIOS vNext runtime."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ExecutionResult:
    task_id: str
    status: str
    value: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == "completed" and self.error is None

    @classmethod
    def success(cls, task_id, value=None, metadata=None):
        return cls(task_id, "completed", value=value, metadata=dict(metadata or {}))

    @classmethod
    def failure(cls, task_id, error, metadata=None):
        return cls(task_id, "failed", error=str(error), metadata=dict(metadata or {}))
