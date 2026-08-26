import asyncio

from execution.checkpoint import Checkpoint
from execution.coordinator import ExecutionCoordinator
from execution.persistence import ExecutionStore
from kernel.checkpoint_recovery import CheckpointRecovery
from kernel.scheduler import AgentTask, Scheduler


class CrashOnceRunner:
    def __init__(self):
        self.calls = 0

    async def run(self, goal, plan, context):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("simulated crash")
        return {"answer": goal}


class Checkpoints:
    def __init__(self):
        self._items = {}

    def save(self, checkpoint):
        self._items[checkpoint.task_id] = checkpoint

    def load(self, task_id):
        return self._items.get(task_id)

    def delete(self, task_id):
        return self._items.pop(task_id, None)


def test_crash_checkpoint_restart_and_replay():
    persistence = ExecutionStore()
    checkpoints = Checkpoints()
    runner = CrashOnceRunner()
    coordinator = ExecutionCoordinator(agent_runner=runner, persistence=persistence)

    first = Scheduler(executor=coordinator, persistence=persistence, checkpoint_store=checkpoints)
    asyncio.run(first.submit(AgentTask("crash-1", "agent", {"goal": "resume", "task_id": "crash-1"}, max_attempts=1)))
    asyncio.run(first.run_until_idle())

    assert persistence.load_result("crash-1") is None
    assert checkpoints.load("crash-1") is not None

    second = Scheduler(executor=coordinator, persistence=persistence, checkpoint_store=checkpoints)
    recovery = CheckpointRecovery(checkpoints, persistence)
    asyncio.run(recovery.restore(second))
    asyncio.run(second.run_until_idle())

    assert persistence.load_result("crash-1") is not None
    assert runner.calls == 2
    assert checkpoints.load("crash-1") is None

    replay = Scheduler(executor=coordinator, persistence=persistence, checkpoint_store=checkpoints)
    task = AgentTask("crash-1", "agent", {"goal": "resume", "task_id": "crash-1"})
    asyncio.run(replay.submit(task))
    assert runner.calls == 2
    assert replay.queue.qsize() == 0
