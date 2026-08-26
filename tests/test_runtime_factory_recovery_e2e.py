import asyncio

from execution.persistence import ExecutionStore
from kernel.factory import KernelFactory
from kernel.scheduler import AgentTask, Scheduler


class Container:
    def __init__(self, persistence, scheduler):
        self.services = {
            "bootstrap": object(),
            "kernel": type("Kernel", (), {})(),
            "agent_manager": object(),
            "persistence": persistence,
            "scheduler": scheduler,
        }

    def list_services(self):
        return list(self.services)

    def has(self, name):
        return name in self.services

    def resolve(self, name):
        return self.services[name]


def test_factory_runtime_owns_one_recovery_path():
    async def scenario():
        persistence = ExecutionStore()

        async def executor(payload):
            return {"answer": payload["goal"]}

        scheduler = Scheduler(executor=executor, persistence=persistence)
        context = KernelFactory(Container(persistence, scheduler)).create_runtime()
        assert context.scheduler is scheduler
        assert context.checkpoint_store is not None
        recovery = context._checkpoint_recovery
        assert recovery is not None

        first = await context.recover()
        second = await context.recover()
        assert first is recovery
        assert second is recovery

        await scheduler.submit(AgentTask("factory-1", "agent", {"goal": "hello", "task_id": "factory-1"}))
        await scheduler.run_until_idle()
        assert persistence.load_result("factory-1") is not None

        before = context._checkpoint_recovery
        await context.execute("hello", "factory-1")
        assert context._checkpoint_recovery is before

    asyncio.run(scenario())
