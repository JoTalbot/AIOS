"""Checkpoint contracts backed by the execution lifecycle store."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from execution.persistence import ExecutionStore


@dataclass
class Checkpoint:
    task_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    attempt: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class CheckpointStore:
    """Compatibility facade over the canonical ExecutionStore."""

    def __init__(self, persistence: Optional[ExecutionStore] = None):
        self.persistence = persistence or ExecutionStore()

    def save(self, checkpoint: Checkpoint) -> Checkpoint:
        self.persistence.save_checkpoint(checkpoint)
        return checkpoint

    def load(self, task_id: str) -> Optional[Checkpoint]:
        return self.persistence.load_checkpoint(task_id)

    def delete(self, task_id: str) -> None:
        self.persistence.delete_checkpoint(task_id)

    @property
    def _items(self):
        """Compatibility view for legacy recovery code."""
        return {
            task_id: state["checkpoint"]
            for task_id, state in self.persistence._states.items()
            if isinstance(state, dict) and state.get("status") == "checkpoint"
        }
