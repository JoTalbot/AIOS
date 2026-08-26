import asyncio

from execution.checkpoint import Checkpoint
from execution.coordinator import ExecutionCoordinator
from execution.persistence import ExecutionStore
from kernel.factory import KernelFactory
from kernel.scheduler import Scheduler


class Container:
    def __init__(self, persistence, scheduler, execution, planner, agent):
        self.services = {
            "bootstrap": object(),
            "kernel": type("Kernel", (), {"attach_orchestrator": lambda self, value: setattr(self, "orchestrator", value)})(),
            "agent_manager": object(), "persistence": persistence,
            "scheduler": scheduler, "execution": execution,
            "planner": planner, "agent": agent,
        }
    def list_services(self): return list(self.services)
    def has(self, name): return name in self.services
    def resolve(self, name): return self.services[name]


class Planner:
    async def plan(self, goal, context=None):
        return {"goal": goal}


class Agent:
    pass


class Runner:
    def __init__(self):
        self.calls = 0
    async def run(self, goal, plan, context):
        self.calls += 1
        return {"answer": goal}


def test_fresh_runtime_recovers_persisted_checkpoint_and_replays_without_second_execution():
    async def scenario():
        persistence = ExecutionStore()
        runner = Runner()
        execution = ExecutionCoordinator(agent_runner=runner, persistence=persistence)

        first_scheduler = Scheduler(persistence=persistence)
        first = KernelFactory(Container(persistence, first_scheduler, execution, Planner(), Agent())).create_runtime()
        first.checkpoint_store.save(Checkpoint("fresh-runtime-1", {"task_payload": {"agent": "agent", "goal": "resume", "task_id": "fresh-runtime-1"}}, 1))

        second_scheduler = Scheduler(persistence=persistence)
        second = KernelFactory(Container(persistence, second_scheduler, execution, Planner(), Agent())).create_runtime()
        restored = await second.recover()
        assert len(restored) == 1
        await second_scheduler.start()
        await second_scheduler.run_until_idle()

        assert persistence.load_result("fresh-runtime-1") is not None
        assert runner.calls == 1
        assert persistence.load_checkpoint("fresh-runtime-1") is None

        await second_scheduler.submit(__import__("kernel.scheduler", fromlist=["AgentTask"]).AgentTask("fresh-runtime-1", "agent", {"goal": "resume", "task_id": "fresh-runtime-1"}))
        assert runner.calls == 1
        await second.stop_async()

    asyncio.run(scenario())
