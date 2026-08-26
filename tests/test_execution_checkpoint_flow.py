import asyncio

from execution import Checkpoint, CheckpointStore
from kernel.scheduler import AgentTask, Scheduler, TaskState


class FlakyExecutor:
    def __init__(self):
        self.calls = 0

    async def __call__(self, payload):
        self.calls += 1
        if self.calls == 1:
            payload["progress"] = "checkpointed"
            raise RuntimeError("transient")
        assert payload["progress"] == "checkpointed"
        return {"answer": "resumed"}


def test_scheduler_retries_from_checkpoint():
    async def scenario():
        store = CheckpointStore()
        executor = FlakyExecutor()
        scheduler = Scheduler(executor=executor, checkpoint_store=store)
        task = AgentTask("checkpoint-1", "agent", {"input": "x"}, max_attempts=2)

        await scheduler.submit(task)
        await scheduler.run_until_idle()
        await scheduler.stop()

        assert task.state is TaskState.DONE
        assert task.result.ok
        assert task.result.value == {"answer": "resumed"}
        assert executor.calls == 2
        checkpoint = store.load(task.id)
        assert isinstance(checkpoint, Checkpoint)
        assert checkpoint.attempt == 2

    asyncio.run(scenario())
