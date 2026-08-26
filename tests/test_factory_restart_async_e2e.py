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
            "agent_manager": object(), "persistence": persistence,
            "scheduler": scheduler, "execution": execution,
        }
    def list_services(self): return list(self.services)
    def has(self, name): return name in self.services
    def resolve(self, name): return self.services[name]


class BlockingRunner:
    def __init__(self):
        self.calls = 0; self.started = asyncio.Event(); self.release = asyncio.Event()
    async def run(self, goal, plan, context):
        self.calls += 1; self.started.set(); await self.release.wait()
        return {"answer": goal}


def test_factory_runtime_restart_async_recovers_cancelled_task_once():
    async def scenario():
        persistence = ExecutionStore(); scheduler = Scheduler(persistence=persistence)
        runner = BlockingRunner(); execution = ExecutionCoordinator(agent_runner=runner, persistence=persistence)
        context = KernelFactory(Container(persistence, scheduler, execution)).create_runtime()
        task = AgentTask("restart-e2e-1", "agent", {"goal": "resume", "task_id": "restart-e2e-1"})
        await scheduler.submit(task); await context.start_async(); await runner.started.wait()
        worker = scheduler._worker_tasks[0]; worker.cancel(); await asyncio.gather(worker, return_exceptions=True)
        assert context.checkpoint_store.load("restart-e2e-1") is not None
        await context.restart_async(); runner.release.set(); await scheduler.run_until_idle()
        assert persistence.load_result("restart-e2e-1") is not None
        assert runner.calls == 2
        await scheduler.submit(AgentTask("restart-e2e-1", "agent", {"goal": "resume", "task_id": "restart-e2e-1"}))
        assert runner.calls == 2
        await context.stop_async()
    asyncio.run(scenario())
