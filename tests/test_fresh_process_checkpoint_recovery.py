from execution.checkpoint import Checkpoint
from execution.checkpoint_adapter import PersistenceCheckpointStore
from execution.persistence import ExecutionStore


def test_checkpoint_survives_new_checkpoint_store_instance():
    persistence = ExecutionStore()
    first = PersistenceCheckpointStore(persistence)
    checkpoint = Checkpoint("fresh-process-1", {"task_payload": {"agent": "agent", "goal": "resume"}}, 2)
    first.save(checkpoint)

    second = PersistenceCheckpointStore(persistence)
    restored = second.load("fresh-process-1")
    assert restored == checkpoint

    second.delete("fresh-process-1")
    third = PersistenceCheckpointStore(persistence)
    assert third.load("fresh-process-1") is None
