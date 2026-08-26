import asyncio

from execution.checkpoint import Checkpoint
from execution.persistence import ExecutionStore
from kernel.checkpoint_recovery import CheckpointRecovery
from kernel.scheduler import Scheduler


class Store:
    def __init__(self, items):
        self._items = items


def test_completed_persistent_result_wins_over_stale_checkpoint():
    persistence = ExecutionStore()
    persistence.save_result("done", {"answer": "already-complete"})
    checkpoint = Checkpoint("done", {"task_payload": {"agent": "agent", "goal": "repeat"}}, 1)
    scheduler = Scheduler()

    restored = asyncio.run(CheckpointRecovery(Store({"done": checkpoint}), persistence).restore(scheduler))

    assert restored == []
    assert scheduler.queue.qsize() == 0
