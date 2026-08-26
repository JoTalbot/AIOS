"""AIOS v20 Memory Fabric foundation.

Unified memory abstraction for future short-term, episodic and semantic
memory backends.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class MemoryRecord:
    """Single memory event stored in the fabric."""

    content: str
    category: str = "episodic"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryFabric:
    """Minimal in-process memory layer for AIOS v20 agents."""

    def __init__(self) -> None:
        self._records: list[MemoryRecord] = []

    def remember(self, content: str, category: str = "episodic") -> MemoryRecord:
        record = MemoryRecord(content=content, category=category)
        self._records.append(record)
        return record

    def recall(self, category: str | None = None) -> list[MemoryRecord]:
        if category is None:
            return list(self._records)
        return [r for r in self._records if r.category == category]
