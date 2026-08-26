import asyncio

from execution.checkpoint import Checkpoint
from kernel.checkpoint_recovery import CheckpointRecovery
from kernel.scheduler import AgentTask, Scheduler, TaskState


class Store:
    def __init__(self):
        self._items = {}
        self.deleted = []

    def save(self, checkpoint):
        self._items[checkpoint.task_id] = checkpoint

    def load(self, task_id):
        return self._items.get(task_id)

    def delete(self, task_id):
        self.deleted.append(task_id)
        self._items.pop(task_id, None)


def test_terminal_checkpoint_is_not_executed_twice():
    async def scenario():
        store = Store()
        calls = []

        async def executor(payload):
            calls.append(payload["task_id"])
            return "done"

        scheduler = Scheduler(executor=executor, checkpoint_store=store)
        task = AgentTask("once", "agent", {"task_id": "once"})
        await scheduler.submit(task)
        await scheduler.run_until_idle()
        assert calls == ["once"]
        assert store.deleted == ["once"]

        terminal = Checkpoint("once", {"task_payload": {"task_id": "once", "result": "done"}}, 1)
        store.save(terminal)
        scheduler2 = Scheduler(executor=executor, checkpoint_store=store)
        await CheckpointRecovery(store).restore(scheduler2)
        assert scheduler2.queue.qsize() == 0

    asyncio.run(scenario())


def test_restore_is_idempotent():
    async def scenario():
        store = Store()
        store.save(Checkpoint("r", {"task_payload": {"task_id": "r", "step": "resume"}}, 1))
        scheduler = Scheduler(checkpoint_store=store)
        first = await CheckpointRecovery(store).restore(scheduler)
        second = await CheckpointRecovery(store).restore(scheduler)
        assert len(first) == 1
        assert second == []
        assert scheduler.queue.qsize() == 1
        assert scheduler.tasks["r"].state is TaskState.RESTORING

    asyncio.run(scenario())
