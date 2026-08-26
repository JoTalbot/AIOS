import pytest

from agents.planner import Planner
from execution.coordinator import ExecutionCoordinator
from kernel.factory import KernelFactory
from kernel.kernel import Kernel
from kernel.memory import MemoryOS
from kernel.scheduler import Scheduler


class Agent:
    async def run(self, goal, plan, context):
        return {"goal": goal, "steps": len(plan)}


class Tools:
    async def execute(self, result, context=None):
        return {**result, "tool": "ok"}


class Container:
    def __init__(self):
        memory = MemoryOS()
        self.services = {
            "kernel": Kernel(),
            "agent_manager": object(),
            "bootstrap": object(),
            "planner": Planner(memory),
            "scheduler": Scheduler(),
            "agent": Agent(),
            "execution": ExecutionCoordinator(Agent(), Tools(), memory),
        }

    def list_services(self):
        return list(self.services)

    def has(self, name):
        return name in self.services

    def resolve(self, name):
        return self.services[name]

    def register(self, name, service):
        self.services[name] = service


@pytest.mark.asyncio
async def test_factory_wires_kernel_to_vnext_entrypoint():
    container = Container()
    context = KernelFactory(container).create_runtime()

    assert context.orchestrator is not None
    assert container.services["kernel"].orchestrator is context.orchestrator

    result = await container.services["kernel"].execute("factory goal", "factory-task")
    assert result.status == "completed"
    assert result.result["result"]["tool"] == "ok"
