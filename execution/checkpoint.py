"""Checkpoint contracts for resumable AIOS vNext execution."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Checkpoint:
    task_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    attempt: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class CheckpointStore:
    """Small persistence-neutral checkpoint store.

    A persistence adapter can implement ``save``/``load`` externally; this
    in-memory implementation provides the runtime contract and safe defaults.
    """

    def __init__(self):
        self._items: Dict[str, Checkpoint] = {}

    def save(self, checkpoint: Checkpoint) -> Checkpoint:
        self._items[checkpoint.task_id] = checkpoint
        return checkpoint

    def load(self, task_id: str) -> Optional[Checkpoint]:
        return self._items.get(task_id)

    def delete(self, task_id: str) -> None:
        self._items.pop(task_id, None)
