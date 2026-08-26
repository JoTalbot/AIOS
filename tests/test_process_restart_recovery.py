import asyncio

from execution.checkpoint import Checkpoint
from kernel.scheduler import AgentTask, Scheduler, TaskState
from kernel.checkpoint_recovery import CheckpointRecovery


class PersistentStore:
    def __init__(self):
        self._items = {}

    def save(self, checkpoint):
        self._items[checkpoint.task_id] = checkpoint

    def load(self, task_id):
        return self._items.get(task_id)


class Process:
    def __init__(self, store, calls):
        self.store = store
        self.calls = calls
        self.scheduler = Scheduler(checkpoint_store=store, executor=self.execute)

    async def execute(self, payload):
        self.calls.append(payload["step"])
        if payload["step"] == "start":
            raise RuntimeError("simulated process crash")
        return payload["step"]


async def scenario():
    store = PersistentStore()
    calls = []

    first = Process(store, calls)
    task = AgentTask("process-restart-1", "agent", {"task_id": "process-restart-1", "step": "start"}, max_attempts=1)
    await first.scheduler.submit(task)
    await first.scheduler.run_until_idle()
    assert task.state is TaskState.FAILED

    checkpoint = store.load(task.id)
    checkpoint.payload["task_payload"]["step"] = "resume"

    second = Process(store, calls)
    restored = await CheckpointRecovery(store).restore(second.scheduler)
    assert len(restored) == 1
    restored[0].payload["step"] = "resume"
    await second.scheduler.run_until_idle()
    assert second.scheduler.tasks[task.id].state is TaskState.DONE
    assert calls == ["start", "resume"]


def test_process_restart_restores_and_resumes_checkpointed_task():
    asyncio.run(scenario())
