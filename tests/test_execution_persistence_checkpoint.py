from execution import Checkpoint, PersistenceCheckpointStore


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
    checkpoint = Checkpoint("task-1", {"progress": "ready"}, 2)

    assert store.save(checkpoint) is checkpoint
    restored = PersistenceCheckpointStore(persistence).load("task-1")
    assert restored == checkpoint

    assert store.delete("task-1") is None
    assert store.load("task-1") is None
