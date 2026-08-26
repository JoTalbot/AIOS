import asyncio

from runtime.vnext_orchestrator import VNextOrchestrator


class Scheduler:
    def __init__(self):
        self.executor = None
        self.started = 0
        self.stopped = 0

    async def start(self):
        self.started += 1

    async def stop(self):
        self.stopped += 1

    async def submit(self, task):
        self.task = task

    async def run_until_idle(self):
        self.task.payload["result"] = "ok"
        self.task.state = type("State", (), {"value": "done"})()


class Planner:
    async def create_plan(self, goal):
        return [goal]


class Agent:
    def __str__(self):
        return "agent"


def test_orchestrator_start_is_idempotent_and_stop_is_safe():
    async def scenario():
        scheduler = Scheduler()
        orchestrator = VNextOrchestrator(Planner(), scheduler, Agent())
        await orchestrator.start()
        await orchestrator.start()
        assert scheduler.started == 1
        await orchestrator.stop()
        await orchestrator.stop()
        assert scheduler.stopped == 1

    asyncio.run(scenario())
