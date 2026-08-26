"""Persistent operator queues for quarantine and manual recovery decisions."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class RecoveryQueueItem:
    execution_id: str
    action: str
    reason: str
    attempt: int
    correlation_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved: bool = False


class RecoveryQueue:
    def __init__(self, path: str = "data/recovery_queue.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def enqueue(self, item: RecoveryQueueItem) -> RecoveryQueueItem:
        if any(x.execution_id == item.execution_id and x.action == item.action and not x.resolved for x in self.items()):
            return item
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
        return item

    def items(self, action: Optional[str] = None, unresolved_only: bool = False):
        if not self.path.exists():
            return []
        result = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = RecoveryQueueItem(**json.loads(line))
            if (action is None or item.action == action) and (not unresolved_only or not item.resolved):
                result.append(item)
        return result
