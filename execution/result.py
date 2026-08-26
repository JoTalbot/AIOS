"""Typed execution results used across the AIOS vNext runtime."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

from .status import EXECUTION_COMPLETED_STATUS, EXECUTION_FAILED_STATUS


@dataclass
class ExecutionResult:
    task_id: str
    status: str
    value: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == EXECUTION_COMPLETED_STATUS and self.error is None

    def to_dict(self) -> Dict[str, Any]:
        """Return the stable wire/persistence representation."""
        return asdict(self)

    def to_event_payload(self) -> Dict[str, Any]:
        """Return only fields intended for execution event payloads."""
        return self.to_dict()

    @classmethod
    def success(cls, task_id, value=None, metadata=None):
        return cls(task_id, EXECUTION_COMPLETED_STATUS, value=value, metadata=dict(metadata or {}))

    @classmethod
    def failure(cls, task_id, error, metadata=None):
        return cls(task_id, EXECUTION_FAILED_STATUS, error=str(error), metadata=dict(metadata or {}))
