import asyncio
from dataclasses import dataclass, field
from enum import Enum


class TaskState(Enum):
    CREATED = "created"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    RETRYING = "retrying"
    RESTORING = "restoring"


@dataclass
class AgentTask:
    id: str
    agent: str
    payload: dict
    state: TaskState = TaskState.CREATED
    attempts: int = 0
    max_attempts: int = 3
    checkpoint: dict | None = None
    error: str | None = None
    history: list[dict] = field(default_factory=list)


class Scheduler:
    def __init__(self, workers=1, executor=None, recovery=None, checkpoint_store=None):
        self.queue = asyncio.Queue()
        self.tasks = {}
        self.workers = max(1, workers)
        self.executor = executor
        self.recovery = recovery
        self.checkpoint_store = checkpoint_store
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
                await self._execute_with_recovery(task)
            finally:
                self.queue.task_done()

    async def _execute_with_recovery(self, task):
        while True:
            task.state = TaskState.RUNNING
            task.attempts += 1
            self._restore_checkpoint(task)
            try:
                task.payload["result"] = await self.execute(task)
                task.state = TaskState.DONE
                task.error = None
                self._save_checkpoint(task)
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                task.error = str(exc)
                task.history.append({"attempt": task.attempts, "error": task.error})
                action = self._recovery_action(task, exc)
                if action == "retry":
                    task.state = TaskState.RETRYING
                    self._save_checkpoint(task)
                    continue
                if action == "restore" and self._restore_checkpoint(task):
                    task.state = TaskState.RESTORING
                    continue
                task.state = TaskState.FAILED
                return

    def _recovery_action(self, task, error):
        if task.attempts < task.max_attempts:
            return "retry"
        if self.recovery and hasattr(self.recovery, "evaluate"):
            from execution.recovery import RecoverySignal
            metadata = {"checkpoint": "available"} if self._has_checkpoint(task) else {}
            decision = self.recovery.evaluate(RecoverySignal(task.agent, str(error), task.attempts, metadata))
            return getattr(getattr(decision, "action", None), "value", "abort")
        return "abort"

    def _has_checkpoint(self, task):
        if task.checkpoint is not None:
            return True
        return bool(self.checkpoint_store and self.checkpoint_store.load(task.id))

    def _save_checkpoint(self, task):
        if self.checkpoint_store is None:
            return
        from execution.checkpoint import Checkpoint
        payload = dict(task.checkpoint or {})
        payload.setdefault("task_payload", dict(task.payload))
        self.checkpoint_store.save(Checkpoint(task.id, payload, task.attempts))

    def _restore_checkpoint(self, task):
        checkpoint = None
        if self.checkpoint_store is not None:
            checkpoint = self.checkpoint_store.load(task.id)
        if checkpoint is None and task.checkpoint is not None:
            task.payload.update(task.checkpoint)
            return True
        if checkpoint is None:
            return False
        payload = dict(checkpoint.payload)
        task.payload.update(payload.get("task_payload", payload))
        return True

    async def execute(self, task):
        if self.executor is not None:
            value = self.executor(task.payload)
            return await value if hasattr(value, "__await__") else value
        await asyncio.sleep(0)
        return {"agent": task.agent, "status": "completed"}
