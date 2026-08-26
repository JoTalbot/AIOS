from execution.checkpoint import Checkpoint
from execution.checkpoint_adapter import PersistenceCheckpointStore


class Persistence:
    def __init__(self):
        self.items = {}

    def save_checkpoint(self, checkpoint):
        self.items[checkpoint.task_id] = checkpoint

    def load_checkpoint(self, task_id):
        return self.items.get(task_id)

    def delete_checkpoint(self, task_id):
        self.items.pop(task_id, None)


def test_persistence_checkpoint_store_round_trip():
    persistence = Persistence()
    store = PersistenceCheckpointStore(persistence)
    checkpoint = Checkpoint("task-1", {"step": 4})

    store.save(checkpoint)
    assert store.load("task-1") is checkpoint
    assert persistence.items["task-1"] is checkpoint

    store.delete("task-1")
    assert store.load("task-1") is None
