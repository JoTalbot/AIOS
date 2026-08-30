from dataclasses import dataclass
from typing import Any


@dataclass
class ExecutionContext:
    agent_id: str
    action: str
    metadata: dict[str, Any] | None = None
