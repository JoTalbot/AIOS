from execution.checkpoint_adapter import PersistenceCheckpointStore


class EmptyPersistence:
    def load_checkpoint(self, task_id):
        return None

    def delete_checkpoint(self, task_id):
        pass


def test_adapter_falls_back_to_local_checkpoint_when_persistence_is_empty():
    store = PersistenceCheckpointStore(EmptyPersistence())
    from execution.checkpoint import Checkpoint
    checkpoint = Checkpoint("task-1", {"step": 1})
    store.save(checkpoint)
    assert store.load("task-1") is checkpoint
    store.delete("task-1")
    assert store.load("task-1") is None
