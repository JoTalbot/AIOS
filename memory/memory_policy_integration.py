from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class MemoryContext:
    key: str
    value: Any
    confidence: float = 0.0


class MemoryPolicyIntegration:
    """Bridge between agent memory and policy decisions."""

    def __init__(self, memory=None):
        self.memory = memory
        self.cache: Dict[str, MemoryContext] = {}

    def remember(self, key: str, value: Any, confidence: float = 1.0):
        self.cache[key] = MemoryContext(key, value, confidence)

    def recall(self, key: str) -> Optional[MemoryContext]:
        if key in self.cache:
            return self.cache[key]
        if self.memory and hasattr(self.memory, "get"):
            value = self.memory.get(key)
            if value is not None:
                return MemoryContext(key, value, 0.5)
        return None

    def enrich_policy_context(self, decision_key: str) -> Dict[str, Any]:
        context = self.recall(decision_key)
        if not context:
            return {}
        return {
            "memory_value": context.value,
            "memory_confidence": context.confidence,
        }
