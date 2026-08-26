import asyncio
from dataclasses import dataclass
from enum import Enum


class TaskState(Enum):
    CREATED = "created"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class AgentTask:
    id: str
    agent: str
    payload: dict
    state: TaskState = TaskState.CREATED


class Scheduler:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.tasks = {}

    async def submit(self, task: AgentTask):
        self.tasks[task.id] = task
        await self.queue.put(task)

    async def worker(self):
        while True:
            task = await self.queue.get()
            try:
                task.state = TaskState.RUNNING
                task.payload["result"] = await self.execute(task)
                task.state = TaskState.DONE
            except Exception as exc:
                task.payload["error"] = str(exc)
                task.state = TaskState.FAILED
            finally:
                self.queue.task_done()

    async def execute(self, task):
        await asyncio.sleep(0)
        return {"agent": task.agent, "status": "completed"}
