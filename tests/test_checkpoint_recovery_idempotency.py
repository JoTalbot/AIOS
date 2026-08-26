import asyncio

from execution.checkpoint import Checkpoint, CheckpointStore
from execution.persistence import ExecutionStore
from kernel.checkpoint_recovery import CheckpointRecovery
from kernel.scheduler import Scheduler


def test_checkpoint_recovery_restores_each_scheduler_once():
    async def scenario():
        persistence = ExecutionStore()
        store = CheckpointStore(persistence)
        store.save(Checkpoint("recover-once", {"task_payload": {"agent": "agent", "goal": "resume"}}, 1))
        scheduler = Scheduler(persistence=persistence)
        recovery = CheckpointRecovery(store, persistence)

        first = await recovery.restore(scheduler)
        second = await recovery.restore(scheduler)
        assert len(first) == 1
        assert second == []
        assert scheduler.queue.qsize() == 1
        assert len(scheduler.tasks) == 1

    asyncio.run(scenario())
