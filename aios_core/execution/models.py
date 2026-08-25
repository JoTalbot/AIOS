"""Immutable action and execution observation models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class Action:
    """A requested capability execution.

    The action contains only serialisable intent. Capability handlers are resolved
    by the runtime and are never embedded in an action.
    """

    capability: str
    arguments: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid4().hex[:12])


@dataclass(frozen=True)
class Observation:
    """Result of executing an action."""

    action_id: str
    success: bool
    result: Any = None
    error: str | None = None

    @classmethod
    def from_result(cls, action: Action, result: Any) -> Observation:
        return cls(action_id=action.id, success=True, result=result)

    @classmethod
    def failed(cls, action: Action, error: str) -> Observation:
        return cls(action_id=action.id, success=False, error=error)
