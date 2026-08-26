import asyncio

from execution.checkpoint import CheckpointStore
from execution.persistence import ExecutionStore
from kernel.scheduler import AgentTask, Scheduler


class BlockingExecutor:
    def __init__(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def __call__(self, payload):
        self.started.set()
        await self.release.wait()
        return {"ok": True}


def test_worker_cancellation_preserves_checkpoint_and_queue_accounting():
    async def scenario():
        persistence = ExecutionStore()
        checkpoints = CheckpointStore(persistence)
        executor = BlockingExecutor()
        scheduler = Scheduler(executor=executor, persistence=persistence, checkpoint_store=checkpoints)
        await scheduler.submit(AgentTask("shutdown-1", "agent", {"goal": "wait", "task_id": "shutdown-1"}))
        await scheduler.start()
        await executor.started.wait()
        worker = scheduler._worker_tasks[0]
        worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)
        assert checkpoints.load("shutdown-1") is not None
        assert persistence.load_result("shutdown-1") is None
        assert scheduler.queue.qsize() == 0
        scheduler._worker_tasks = []

    asyncio.run(scenario())
