import asyncio

from execution.checkpoint import Checkpoint, CheckpointStore
from execution.persistence import ExecutionStore
from kernel.checkpoint_recovery import CheckpointRecovery
from kernel.scheduler import Scheduler


class RuntimeStore(ExecutionStore):
    pass


def test_crash_restart_restores_checkpoint_but_completed_result_wins():
    persistence = RuntimeStore()
    checkpoints = CheckpointStore(persistence)
    checkpoints.save(Checkpoint("task-1", {"task_payload": {"agent": "agent", "goal": "continue"}}, 1))

    scheduler = Scheduler()
    restored = asyncio.run(CheckpointRecovery(checkpoints, persistence).restore(scheduler))
    assert [task.task_id for task in restored] == ["task-1"]
    assert scheduler.queue.qsize() == 1

    # Simulate the execution reaching a terminal state after restart.
    persistence.save_result("task-1", {"status": "completed", "value": "done"})

    # A second recovery pass must not enqueue the task again.
    restarted_scheduler = Scheduler()
    restored_again = asyncio.run(CheckpointRecovery(checkpoints, persistence).restore(restarted_scheduler))
    assert restored_again == []
    assert restarted_scheduler.queue.qsize() == 0
    assert persistence.load_result("task-1") == {"status": "completed", "value": "done"}
