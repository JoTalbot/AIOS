import asyncio

from execution.checkpoint import CheckpointStore
from execution.coordinator import ExecutionCoordinator
from execution.persistence import ExecutionStore
from kernel.checkpoint_recovery import CheckpointRecovery
from kernel.scheduler import AgentTask, Scheduler, TaskState


class BlockingRunner:
    def __init__(self):
        self.calls = 0
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def run(self, goal, plan, context):
        self.calls += 1
        self.started.set()
        await self.release.wait()
        return {"answer": goal}


def test_cancellation_leaves_checkpoint_for_restart():
    async def scenario():
        persistence = ExecutionStore()
        checkpoints = CheckpointStore(persistence)
        runner = BlockingRunner()
        coordinator = ExecutionCoordinator(agent_runner=runner, persistence=persistence)
        scheduler = Scheduler(executor=coordinator, persistence=persistence, checkpoint_store=checkpoints)
        await scheduler.submit(AgentTask("cancel-1", "agent", {"goal": "resume", "task_id": "cancel-1"}))
        await scheduler.start()
        await runner.started.wait()
        scheduler._worker_tasks[0].cancel()
        await asyncio.gather(*scheduler._worker_tasks, return_exceptions=True)
        assert persistence.load_result("cancel-1") is None
        assert checkpoints.load("cancel-1") is not None

        runner.release.set()
        fresh = Scheduler(executor=coordinator, persistence=persistence, checkpoint_store=checkpoints)
        await CheckpointRecovery(checkpoints, persistence).restore(fresh)
        await fresh.run_until_idle()
        assert persistence.load_result("cancel-1") is not None
        assert runner.calls == 2
        assert checkpoints.load("cancel-1") is None

        replay = Scheduler(executor=coordinator, persistence=persistence, checkpoint_store=checkpoints)
        await replay.submit(AgentTask("cancel-1", "agent", {"goal": "resume", "task_id": "cancel-1"}))
        assert replay.queue.qsize() == 0
        assert runner.calls == 2

    asyncio.run(scenario())
