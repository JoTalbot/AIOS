import asyncio

from api.application import APIApplication
from runtime.vnext_orchestrator import VNextOrchestrator
from kernel.scheduler import Scheduler


class Planner:
    async def create_plan(self, goal):
        return {"steps": [goal]}


class Agent:
    def __str__(self):
        return "agent"


class Execution:
    def __init__(self):
        self.calls = 0

    async def execute(self, payload):
        self.calls += 1
        return {"executed": payload["goal"], "plan": payload["plan"]}


class Runtime:
    def __init__(self):
        execution = Execution()
        self.execution = execution
        self.orchestrator = VNextOrchestrator(Planner(), Scheduler(), Agent(), execution=execution)

    async def execute(self, goal, task_id, metadata=None):
        return await self.orchestrator.run(goal, task_id, metadata)


def test_api_reaches_orchestrator_scheduler_and_execution():
    runtime = Runtime()
    app = APIApplication(runtime)
    result = asyncio.run(app.handle({"goal": "ship", "task_id": "e2e-1", "metadata": {"source": "api"}}))
    assert result["task_id"] == "e2e-1"
    assert result["result"].status == "completed"
    assert result["result"].result["executed"] == "ship"
    assert runtime.execution.calls == 1
