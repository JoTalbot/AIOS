import asyncio

from execution.checkpoint import CheckpointStore
from execution.coordinator import ExecutionCoordinator
from execution.persistence import ExecutionStore
from kernel.checkpoint_recovery import CheckpointRecovery
from kernel.scheduler import AgentTask, Scheduler


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


def test_cancel_restart_workers_recover_and_replay_once():
    async def scenario():
        persistence = ExecutionStore()
        checkpoints = CheckpointStore(persistence)
        runner = BlockingRunner()
        coordinator = ExecutionCoordinator(agent_runner=runner, persistence=persistence)
        scheduler = Scheduler(executor=coordinator, persistence=persistence, checkpoint_store=checkpoints)

        await scheduler.submit(AgentTask("worker-restart-1", "agent", {"goal": "resume", "task_id": "worker-restart-1"}))
        await scheduler.start()
        await runner.started.wait()
        worker = scheduler._worker_tasks[0]
        worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)
        assert checkpoints.load("worker-restart-1") is not None
        assert persistence.load_result("worker-restart-1") is None

        await scheduler.start()
        await CheckpointRecovery(checkpoints, persistence).restore(scheduler)
        runner.release.set()
        await scheduler.run_until_idle()
        assert persistence.load_result("worker-restart-1") is not None
        assert runner.calls == 2
        assert checkpoints.load("worker-restart-1") is None

        replay = AgentTask("worker-restart-1", "agent", {"goal": "resume", "task_id": "worker-restart-1"})
        await scheduler.submit(replay)
        assert runner.calls == 2

        await scheduler.stop()

    asyncio.run(scenario())
