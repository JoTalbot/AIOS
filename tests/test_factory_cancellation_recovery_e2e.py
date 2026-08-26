import asyncio

from execution.coordinator import ExecutionCoordinator
from execution.persistence import ExecutionStore
from kernel.factory import KernelFactory
from kernel.scheduler import AgentTask, Scheduler


class Container:
    def __init__(self, persistence, scheduler, execution):
        self.services = {
            "bootstrap": object(),
            "kernel": type("Kernel", (), {"attach_orchestrator": lambda self, value: setattr(self, "orchestrator", value)})(),
            "agent_manager": object(),
            "persistence": persistence,
            "scheduler": scheduler,
            "execution": execution,
        }

    def list_services(self):
        return list(self.services)

    def has(self, name):
        return name in self.services

    def resolve(self, name):
        return self.services[name]


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


def test_factory_context_cancel_restart_recover_persist_replay():
    async def scenario():
        persistence = ExecutionStore()
        scheduler = Scheduler(persistence=persistence)
        runner = BlockingRunner()
        execution = ExecutionCoordinator(agent_runner=runner, persistence=persistence)
        context = KernelFactory(Container(persistence, scheduler, execution)).create_runtime()

        task = AgentTask("factory-cancel-1", "agent", {"goal": "resume", "task_id": "factory-cancel-1"})
        await scheduler.submit(task)
        await scheduler.start()
        await runner.started.wait()
        worker = scheduler._worker_tasks[0]
        worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)

        assert context.checkpoint_store.load("factory-cancel-1") is not None
        assert persistence.load_result("factory-cancel-1") is None

        await context.scheduler.start()
        runner.release.set()
        await context.scheduler.run_until_idle()

        assert persistence.load_result("factory-cancel-1") is not None
        assert runner.calls == 2
        assert context.checkpoint_store.load("factory-cancel-1") is None

        replay = AgentTask("factory-cancel-1", "agent", {"goal": "resume", "task_id": "factory-cancel-1"})
        await context.scheduler.submit(replay)
        assert runner.calls == 2
        await context.scheduler.stop()

    asyncio.run(scenario())
