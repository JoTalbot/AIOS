import asyncio
import inspect
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
        existing = self.tasks.get(task.id)
        if existing is not None:
            return existing
        persisted = self.persistence.load_result(task.id) if self.persistence else None
        if persisted is not None:
            task.result = ExecutionResult.from_dict(persisted) if hasattr(ExecutionResult, "from_dict") else persisted
            task.payload["result"] = getattr(task.result, "value", persisted)
            task.state = TaskState.DONE
            self.tasks[task.id] = task
            return task
        self.tasks[task.id] = task
        await self.queue.put(task)
        return task

    async def start(self):
        self._worker_tasks = [worker for worker in self._worker_tasks if not worker.done()]
        if not self._worker_tasks:
            self._worker_tasks = [asyncio.create_task(self.worker()) for _ in range(self.workers)]
        return self

    async def run_until_idle(self):
        await self.start()
        await self.queue.join()

    async def stop(self):
        workers = list(self._worker_tasks)
        self._worker_tasks = []
        for worker in workers:
            worker.cancel()
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)

    async def worker(self):
        while True:
            task = await self.queue.get()
            try:
                await self._execute_with_recovery(task)
            finally:
                self.queue.task_done()

    async def _execute_with_recovery(self, task):
        persisted = self.persistence.load_result(task.id) if self.persistence else None
        if persisted is not None:
            task.result = ExecutionResult.from_dict(persisted) if hasattr(ExecutionResult, "from_dict") else persisted
            task.payload["result"] = getattr(task.result, "value", persisted)
            task.state = TaskState.DONE
            return
        self._record(EXECUTION_STARTED, task, {"attempt": task.attempts + 1})
        while True:
            task.state = TaskState.RUNNING
            task.attempts += 1
            try:
                self._restore_checkpoint(task)
                if self._terminal_checkpoint(task):
                    task.state = TaskState.DONE
                    return
                value = await self.execute(task)
                task.result = value if isinstance(value, ExecutionResult) else ExecutionResult.success(task.id, value=value)
                task.payload["result"] = task.result.value
                task.state = TaskState.DONE
                task.error = None
                if self.persistence:
                    self.persistence.save_result(task.id, task.result.to_dict())
                self._finalize_checkpoint(task)
                self._record(EXECUTION_COMPLETED, task, {"attempt": task.attempts, **task.result.to_event_payload()})
                return
            except asyncio.CancelledError:
                self._save_checkpoint(task)
                task.state = TaskState.RESTORING
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
                if self.persistence:
                    self.persistence.save(task.id, {"status": "failed", "result": task.result.to_dict()})
                self._record(EXECUTION_FAILED, task, {"attempt": task.attempts, **task.result.to_event_payload()})
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
        payload["task_payload"] = dict(task.payload)
        self.checkpoint_store.save(Checkpoint(task.id, payload, task.attempts))

    def _finalize_checkpoint(self, task):
        if self.checkpoint_store is None:
            return
        delete = getattr(self.checkpoint_store, "delete", None)
        if delete is not None:
            delete(task.id)

    def _restore_checkpoint(self, task):
        checkpoint = self.checkpoint_store.load(task.id) if self.checkpoint_store else None
        if checkpoint is None and task.checkpoint is not None:
            task.payload.update(task.checkpoint.get("task_payload", task.checkpoint))
            return True
        if checkpoint is None:
            return False
        payload = dict(checkpoint.payload)
        task.payload.update(payload.get("task_payload", payload))
        task.checkpoint = payload
        return True

    def _terminal_checkpoint(self, task):
        return task.payload.get("result") is not None

    async def execute(self, task):
        if self.executor is not None:
            value = self.executor(task.payload)
            value = await value if inspect.isawaitable(value) else value
            return value if isinstance(value, ExecutionResult) else ExecutionResult.success(task.id, value=value)
        await asyncio.sleep(0)
        return ExecutionResult.success(task.id, value={"agent": task.agent, "status": EXECUTION_COMPLETED_STATUS})
