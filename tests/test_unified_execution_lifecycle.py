from execution.checkpoint import Checkpoint, CheckpointStore
from execution.persistence import ExecutionStore


def test_checkpoint_and_terminal_result_share_one_store():
    persistence = ExecutionStore()
    checkpoints = CheckpointStore(persistence)
    checkpoint = Checkpoint("task-1", {"task_payload": {"agent": "a"}}, 1)

    checkpoints.save(checkpoint)
    assert checkpoints.load("task-1") == checkpoint
    assert persistence.load_checkpoint("task-1") == checkpoint

    persistence.save_result("task-1", {"answer": "done"})
    assert checkpoints.load("task-1") is None
    assert persistence.load_result("task-1") == {"answer": "done"}


def test_checkpoint_delete_is_idempotent():
    persistence = ExecutionStore()
    checkpoints = CheckpointStore(persistence)
    checkpoints.delete("missing")
    checkpoints.save(Checkpoint("task-1", {}, 1))
    checkpoints.delete("task-1")
    checkpoints.delete("task-1")
    assert persistence.load("task-1") is None
