from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Decision:
    action: str
    confidence: float
    explanation: str
    fallback: str = "abort"


@dataclass
class DecisionContext:
    state: Dict[str, Any] = field(default_factory=dict)
    memory: Dict[str, Any] = field(default_factory=dict)
    options: List[str] = field(default_factory=list)
