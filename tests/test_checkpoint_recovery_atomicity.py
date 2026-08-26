import asyncio

from execution.checkpoint import Checkpoint
from kernel.checkpoint_recovery import CheckpointRecovery
from kernel.scheduler import Scheduler


class Store:
    def __init__(self, items):
        self._items = items

    def load(self, task_id):
        return self._items.get(task_id)


async def restore(items):
    scheduler = Scheduler()
    restored = await CheckpointRecovery(Store(items)).restore(scheduler)
    return scheduler, restored


def test_incomplete_checkpoint_is_restored():
    checkpoint = Checkpoint("ok", {"task_payload": {"task_id": "ok", "step": "resume"}}, 1)
    scheduler, restored = asyncio.run(restore({"ok": checkpoint}))
    assert [task.id for task in restored] == ["ok"]
    assert scheduler.queue.qsize() == 1


def test_malformed_checkpoint_is_skipped_atomically():
    checkpoint = Checkpoint("bad", {"unexpected": "shape"}, 1)
    scheduler, restored = asyncio.run(restore({"bad": checkpoint}))
    assert restored == []
    assert scheduler.queue.qsize() == 0
