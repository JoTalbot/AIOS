import pytest

from execution.checkpoint import Checkpoint
from execution.checkpoint_adapter import PersistenceCheckpointStore


class FailingPersistence:
    def save_checkpoint(self, checkpoint):
        raise RuntimeError("persistence unavailable")

    def load_checkpoint(self, task_id):
        raise RuntimeError("persistence unavailable")

    def delete_checkpoint(self, task_id):
        raise RuntimeError("persistence unavailable")


def test_adapter_does_not_swallow_persistence_save_failure():
    store = PersistenceCheckpointStore(FailingPersistence())
    with pytest.raises(RuntimeError, match="persistence unavailable"):
        store.save(Checkpoint("task-1", {"step": 1}))


def test_adapter_does_not_swallow_persistence_load_failure():
    store = PersistenceCheckpointStore(FailingPersistence())
    with pytest.raises(RuntimeError, match="persistence unavailable"):
        store.load("task-1")
