from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionContext:
    task_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
