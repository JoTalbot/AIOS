from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass
class TaskContext:
    task_id: str
    input_data: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExecutionContext:
    task: TaskContext
    state: Dict[str, Any] = field(default_factory=dict)
