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


def test_runtime_context_execute_uses_canonical_execution_and_replay():
    async def scenario():
        persistence = ExecutionStore()
        scheduler = Scheduler(persistence=persistence)

        async def runner(goal, plan, context):
            return {"answer": goal}

        execution = ExecutionCoordinator(agent_runner=runner, persistence=persistence)
        context = KernelFactory(Container(persistence, scheduler, execution)).create_runtime()

        await scheduler.submit(AgentTask("runtime-e2e-1", "agent", {"goal": "hello", "task_id": "runtime-e2e-1"}))
        await scheduler.run_until_idle()
        stored = persistence.load_result("runtime-e2e-1")
        assert stored is not None

        before = execution
        assert context.orchestrator.execution is before
        assert context._checkpoint_recovery is not None
        await context.execute("hello", "runtime-e2e-1")
        assert context.orchestrator.execution is before
        assert persistence.load_result("runtime-e2e-1") is not None

    asyncio.run(scenario())
