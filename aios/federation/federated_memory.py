from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class FederatedMemory:
    """Shared memory abstraction for AIOS federation nodes."""

    entries: Dict[str, Any] = field(default_factory=dict)

    def publish(self, key: str, value: Any) -> None:
        self.entries[key] = value

    def retrieve(self, key: str, default: Any = None) -> Any:
        return self.entries.get(key, default)
