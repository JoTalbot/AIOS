from execution.checkpoint import Checkpoint, CheckpointStore


def test_checkpoint_store_round_trip():
    store = CheckpointStore()
    checkpoint = Checkpoint(
        task_id="task-1",
        payload={"step": 2},
        attempt=3,
        metadata={"source": "scheduler"},
    )

    assert store.save(checkpoint) is checkpoint
    restored = store.load("task-1")
    assert restored is checkpoint
    assert restored.payload["step"] == 2
    assert restored.attempt == 3
    assert restored.metadata["source"] == "scheduler"

    store.delete("task-1")
    assert store.load("task-1") is None
