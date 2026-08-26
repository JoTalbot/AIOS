from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionRequest:
    request_id: str
    actor_id: str
    action: str
    target: str
    parameters: dict[str, Any] = field(default_factory=dict)
    capability_token: str | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyDecision:
    status: str
    reason: str
    constraints: list[str] = field(default_factory=list)
    audit_id: str | None = None
