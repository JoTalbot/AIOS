import asyncio

from execution.checkpoint import Checkpoint, CheckpointStore
from execution.persistence import ExecutionStore
from kernel.checkpoint_recovery import CheckpointRecovery
from kernel.factory import KernelFactory
from kernel.scheduler import Scheduler


class Container:
    def __init__(self, persistence, scheduler):
        self.services = {
            "bootstrap": object(),
            "kernel": type("Kernel", (), {"attach_orchestrator": lambda self, value: setattr(self, "orchestrator", value)})(),
            "agent_manager": object(),
            "persistence": persistence,
            "scheduler": scheduler,
        }

    def list_services(self): return list(self.services)
    def has(self, name): return name in self.services
    def resolve(self, name): return self.services[name]


def test_factory_context_async_restart_recovery_has_no_duplicate_restore():
    async def scenario():
        persistence = ExecutionStore()
        checkpoints = CheckpointStore(persistence)
        checkpoints.save(Checkpoint("restart-once", {"task_payload": {"agent": "agent", "goal": "resume"}}, 1))
        scheduler = Scheduler(persistence=persistence)
        context = KernelFactory(Container(persistence, scheduler)).create_runtime()
        context._checkpoint_recovery = CheckpointRecovery(context.checkpoint_store, context.persistence)

        await context.start_async()
        await asyncio.gather(context.recover(), context.recover())
        await context.start_async()
        assert len(context.scheduler.tasks) == 1
        assert context.scheduler.queue.qsize() == 1
        assert len(context.scheduler._worker_tasks) == 1

        await context.stop_async()
        assert context.scheduler._worker_tasks == []

    asyncio.run(scenario())
