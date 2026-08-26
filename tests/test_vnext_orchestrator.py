import pytest

from runtime.vnext_orchestrator import VNextOrchestrator
from kernel.scheduler import Scheduler


class Planner:
    async def create_plan(self, goal):
        return [{"action": "execute", "goal": goal}]


class Reflection:
    async def evaluate(self, results):
        return {"ok": True, "count": len(results)}


class Agent:
    def __str__(self):
        return "test-agent"


@pytest.mark.asyncio
async def test_vnext_orchestrator_completes_pipeline():
    scheduler = Scheduler()
    orchestrator = VNextOrchestrator(
        planner=Planner(),
        scheduler=scheduler,
        agent=Agent(),
        reflection=Reflection(),
    )

    result = await orchestrator.run("demo", "task-1")

    assert result.status == "completed"
    assert result.goal == "demo"
    assert result.metadata["plan"]
    assert result.metadata["reflection"]["ok"] is True
