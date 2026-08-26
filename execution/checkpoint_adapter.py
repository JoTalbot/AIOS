"""Adapter from runtime persistence facade to the checkpoint contract."""

from execution.checkpoint import Checkpoint, CheckpointStore


class PersistenceCheckpointStore(CheckpointStore):
    """CheckpointStore implementation backed by the same canonical persistence object."""

    def __init__(self, persistence):
        super().__init__(persistence)
        self.persistence = persistence

    def save(self, checkpoint: Checkpoint):
        if self.persistence and hasattr(self.persistence, "save_checkpoint"):
            self.persistence.save_checkpoint(checkpoint)
        return checkpoint

    def load(self, task_id: str):
        if self.persistence and hasattr(self.persistence, "load_checkpoint"):
            return self.persistence.load_checkpoint(task_id)
        return super().load(task_id)

    def delete(self, task_id: str):
        if self.persistence and hasattr(self.persistence, "delete_checkpoint"):
            self.persistence.delete_checkpoint(task_id)
        return None
