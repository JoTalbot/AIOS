import pytest

from agents.planner import Planner
from execution.coordinator import ExecutionCoordinator
from kernel.memory import MemoryOS
from kernel.scheduler import Scheduler
from runtime.vnext_orchestrator import VNextOrchestrator


class Agent:
    async def run(self, goal, plan, context):
        return {"goal": goal, "steps": len(plan)}


class Tools:
    async def execute(self, result, context=None):
        return {**result, "tool": "ok"}


class Events:
    def __init__(self):
        self.events = []

    def publish(self, event, payload=None, source="kernel"):
        self.events.append(event)


class Reflection:
    async def evaluate(self, results):
        return {"accepted": bool(results)}


@pytest.mark.asyncio
async def test_vnext_full_execution_path():
    memory = MemoryOS()
    events = Events()
    execution = ExecutionCoordinator(Agent(), Tools(), memory, events)
    scheduler = Scheduler(executor=execution.execute)
    orchestrator = VNextOrchestrator(
        planner=Planner(memory), scheduler=scheduler, agent=Agent(), reflection=Reflection()
    )

    result = await orchestrator.run("build feature", "task-vnext")

    assert result.status == "completed"
    assert result.result["result"]["tool"] == "ok"
    assert result.metadata["reflection"]["accepted"] is True
    assert events.events == ["execution.started", "execution.completed"]
    assert memory.long_memory
