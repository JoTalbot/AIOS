from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict


@dataclass
class KernelEvent:
    name: str
    source: str = "kernel"
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
