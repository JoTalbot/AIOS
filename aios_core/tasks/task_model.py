"""AIOS task model."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

@dataclass
class AgentTask:
    task_id: str
    action: str
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
