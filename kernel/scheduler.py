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
    def __init__(self, workers=1, executor=None):
        self.queue = asyncio.Queue()
        self.tasks = {}
        self.workers = max(1, workers)
        self.executor = executor
        self._worker_tasks = []

    async def submit(self, task: AgentTask):
        self.tasks[task.id] = task
        await self.queue.put(task)

    async def start(self):
        if not self._worker_tasks:
            self._worker_tasks = [asyncio.create_task(self.worker()) for _ in range(self.workers)]
        return self

    async def run_until_idle(self):
        await self.start()
        await self.queue.join()

    async def stop(self):
        for worker in self._worker_tasks:
            worker.cancel()
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks = []

    async def worker(self):
        while True:
            task = await self.queue.get()
            try:
                task.state = TaskState.RUNNING
                task.payload["result"] = await self.execute(task)
                task.state = TaskState.DONE
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                task.payload["error"] = str(exc)
                task.state = TaskState.FAILED
            finally:
                self.queue.task_done()

    async def execute(self, task):
        if self.executor is not None:
            value = self.executor(task.payload)
            return await value if hasattr(value, "__await__") else value
        await asyncio.sleep(0)
        return {"agent": task.agent, "status": "completed"}
