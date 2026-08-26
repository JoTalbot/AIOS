import asyncio

from execution import ExecutionResult
from kernel.scheduler import AgentTask, Scheduler


class Store:
    def __init__(self):
        self.data = {}

    def save(self, checkpoint):
        self.data[checkpoint.task_id] = checkpoint

    def load(self, task_id):
        return self.data.get(task_id)


async def _run():
    store = Store()
    calls = []

    async def executor(payload):
        calls.append(payload["step"])
        if len(calls) == 1:
            payload["step"] = "after-failure"
            raise RuntimeError("boom")
        return ExecutionResult.success(payload["task_id"], value=payload["step"])

    scheduler = Scheduler(executor=executor, checkpoint_store=store)
    task = AgentTask("resume-1", "agent", {"task_id": "resume-1", "step": "before"}, max_attempts=2)
    await scheduler.submit(task)
    await scheduler.run_until_idle()
    await scheduler.stop()
    return task, calls, store


def test_scheduler_saves_checkpoint_and_resumes_after_failure():
    task, calls, store = asyncio.run(_run())
    assert task.state.value == "completed"
    assert calls == ["before", "after-failure"]
    assert store.load("resume-1") is not None
