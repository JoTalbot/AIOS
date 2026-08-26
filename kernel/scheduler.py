import asyncio
from dataclasses import dataclass, field
from enum import Enum

from execution import ExecutionResult
from execution.event_sink import ExecutionEventSink
from execution.events import EXECUTION_COMPLETED, EXECUTION_FAILED, EXECUTION_RECOVERY, EXECUTION_STARTED, build_event
from execution.status import EXECUTION_COMPLETED_STATUS


class TaskState(Enum):
    CREATED = "created"
    RUNNING = "running"
    DONE = EXECUTION_COMPLETED_STATUS
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
    result: ExecutionResult | None = None


class Scheduler:
    def __init__(self, workers=1, executor=None, recovery=None, checkpoint_store=None, persistence=None, event_sink=None):
        self.queue = asyncio.Queue()
        self.tasks = {}
        self.workers = max(1, workers)
        self.executor = executor
        self.recovery = recovery
        self.checkpoint_store = checkpoint_store
        self.persistence = persistence
        self.event_sink = event_sink or ExecutionEventSink(persistence)
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
        self._record(EXECUTION_STARTED, task, {"attempt": task.attempts + 1})
        while True:
            task.state = TaskState.RUNNING
            task.attempts += 1
            try:
                self._restore_checkpoint(task)
                value = await self.execute(task)
                task.result = value if isinstance(value, ExecutionResult) else ExecutionResult.success(task.id, value=value)
                task.payload["result"] = task.result.value
                task.state = TaskState.DONE
                task.error = None
                self._save_checkpoint(task)
                self._record(EXECUTION_COMPLETED, task, {"attempt": task.attempts})
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                task.error = str(exc)
                task.history.append({"attempt": task.attempts, "error": task.error})
                action = self._recovery_action(task, exc)
                self._record(EXECUTION_RECOVERY, task, {"attempt": task.attempts, "action": action, "error": task.error})
                if action == "retry":
                    task.state = TaskState.RETRYING
                    self._save_checkpoint(task)
                    continue
                if action == "restore" and self._restore_checkpoint(task):
                    task.state = TaskState.RESTORING
                    continue
                task.state = TaskState.FAILED
                task.result = ExecutionResult.failure(task.id, exc, metadata={"attempt": task.attempts})
                self._record(EXECUTION_FAILED, task, {"attempt": task.attempts, "error": task.error})
                return

    def _recovery_action(self, task, error):
        if self.recovery and hasattr(self.recovery, "evaluate"):
            from execution.recovery import RecoverySignal
            metadata = {"checkpoint": "available"} if self._has_checkpoint(task) else {}
            decision = self.recovery.evaluate(RecoverySignal(task.agent, str(error), task.attempts, metadata))
            return getattr(getattr(decision, "action", None), "value", "abort")
        return "retry" if task.attempts < task.max_attempts else "abort"

    def _record(self, event_type, task, data):
        return self.event_sink.emit(build_event(event_type, task.id, **data))

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
        checkpoint = self.checkpoint_store.load(task.id) if self.checkpoint_store else None
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
        return ExecutionResult.success(task.id, value={"agent": task.agent, "status": EXECUTION_COMPLETED_STATUS})
