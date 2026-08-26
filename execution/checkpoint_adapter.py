"""Adapter from runtime persistence facade to the checkpoint contract."""

from execution.checkpoint import Checkpoint, CheckpointStore


class PersistenceCheckpointStore(CheckpointStore):
    """CheckpointStore implementation backed by RuntimePersistenceFacade."""

    def __init__(self, persistence):
        super().__init__()
        self.persistence = persistence

    def save(self, checkpoint: Checkpoint):
        if self.persistence and hasattr(self.persistence, "save_checkpoint"):
            self.persistence.save_checkpoint(checkpoint)
        return super().save(checkpoint)

    def load(self, task_id: str):
        if self.persistence and hasattr(self.persistence, "load_checkpoint"):
            value = self.persistence.load_checkpoint(task_id)
            if isinstance(value, Checkpoint):
                self._items[task_id] = value
        return super().load(task_id)

    def delete(self, task_id: str):
        if self.persistence and hasattr(self.persistence, "delete_checkpoint"):
            self.persistence.delete_checkpoint(task_id)
        return super().delete(task_id)
