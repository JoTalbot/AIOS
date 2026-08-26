import asyncio

from execution.checkpoint import Checkpoint
from execution.checkpoint_adapter import PersistenceCheckpointStore
from execution.persistence import ExecutionStore
from kernel.checkpoint_recovery import CheckpointRecovery
from kernel.runtime_context import RuntimeContext
from kernel.scheduler import Scheduler


class BlockingScheduler(Scheduler):
    pass


def test_new_runtime_context_recovers_persisted_checkpoint_once():
    async def scenario():
        persistence = ExecutionStore()
        adapter = PersistenceCheckpointStore(persistence)
        checkpoint = Checkpoint(
            "fresh-runtime-1",
            {"task_payload": {"agent": "agent", "goal": "resume", "task_id": "fresh-runtime-1"}},
            1,
        )
        adapter.save(checkpoint)

        scheduler = BlockingScheduler(persistence=persistence)
        recovery = CheckpointRecovery(PersistenceCheckpointStore(persistence), persistence)
        context = RuntimeContext(
            persistence=persistence,
            scheduler=scheduler,
            checkpoint_store=PersistenceCheckpointStore(persistence),
            checkpoint_recovery=recovery,
        )

        await context.recover()
        await context.recover()
        assert "fresh-runtime-1" in scheduler.tasks
        assert scheduler.queue.qsize() == 1

    asyncio.run(scenario())
