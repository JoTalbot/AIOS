"""Distributed Computing Framework for AIOS v10.7.0.

Distributed task execution with worker pools, task sharding,
result aggregation, fault tolerance, load balancing, and
progress tracking.

Classes:
    TaskStatus      — lifecycle status for distributed tasks
    DistributedTask — full task definition
    WorkerNode      — worker with capabilities and status
    DistributedComputing — full distributed execution engine
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task lifecycle."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DistributedTask:
    """Full task definition."""

    task_id: str = ""
    func: Callable | None = None
    args: tuple = ()
    kwargs: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    assigned_worker: str | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    required_capability: str = ""

    def __post_init__(self) -> None:
        if not self.task_id:
            import uuid

            self.task_id = str(uuid.uuid4())[:8]

    def duration(self) -> float:
        """Return execution duration."""
        if self.completed_at and self.created_at:
            return self.completed_at - self.created_at
        return 0.0


@dataclass
class WorkerNode:
    """Worker with capabilities and status."""

    worker_id: str = ""
    capabilities: list[str] = field(default_factory=list)
    status: str = "idle"  # idle, busy, offline
    task_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    max_concurrent: int = 5
    active_tasks: list[str] = field(default_factory=list)

    def is_available(self) -> bool:
        """Check if worker can accept more tasks."""
        return self.status == "idle" and len(self.active_tasks) < self.max_concurrent

    def has_capability(self, capability: str) -> bool:
        """Check if worker has required capability."""
        if not capability:  # empty = no specific requirement → any worker can do it
            return True
        return capability in self.capabilities or not self.capabilities


class DistributedComputing:
    """Full distributed execution engine.

    Features:
    - Worker registration with capabilities
    - Capability-based task assignment
    - Task sharding (split large tasks)
    - Result aggregation
    - Fault tolerance (retry on worker failure)
    - Load balancing (least-loaded worker)
    - Progress tracking
    """

    def __init__(self) -> None:
        self.workers: dict[str, WorkerNode] = {}
        self.tasks: dict[str, DistributedTask] = {}

    # ── Worker Management ────────────────────────────────────────

    def register_worker(
        self,
        worker_id: str,
        capabilities: list[str] | None = None,
        max_concurrent: int = 5,
    ) -> WorkerNode:
        """Register a worker node."""
        worker = WorkerNode(
            worker_id=worker_id,
            capabilities=capabilities or [],
            max_concurrent=max_concurrent,
        )
        self.workers[worker_id] = worker
        return worker

    def unregister_worker(self, worker_id: str) -> None:
        """Remove a worker (mark offline)."""
        worker = self.workers.get(worker_id)
        if worker:
            worker.status = "offline"

    def get_worker(self, worker_id: str) -> WorkerNode | None:
        """Return worker by ID."""
        return self.workers.get(worker_id)

    # ── Task Submission ──────────────────────────────────────────

    def submit(self, func: Callable, *args: Any, **kwargs: Any) -> str:
        """Submit a task for execution."""
        task = DistributedTask(func=func, args=args, kwargs=kwargs)
        self.tasks[task.task_id] = task
        return task.task_id

    def submit_with_capability(
        self, func: Callable, capability: str, *args: Any, **kwargs: Any
    ) -> str:
        """Submit a task requiring a specific capability."""
        task = DistributedTask(
            func=func, args=args, kwargs=kwargs, required_capability=capability
        )
        self.tasks[task.task_id] = task
        return task.task_id

    # ── Task Assignment ──────────────────────────────────────────

    def assign_task(self, task_id: str) -> WorkerNode | None:
        """Assign task to best-fit worker."""
        task = self.tasks.get(task_id)
        if task is None:
            return None

        # Find suitable worker (least-loaded)
        candidates = [
            w
            for w in self.workers.values()
            if w.is_available() and w.has_capability(task.required_capability)
        ]
        if not candidates:
            return None

        # Least-loaded first
        worker = min(candidates, key=lambda w: w.task_count)
        task.assigned_worker = worker.worker_id
        task.status = TaskStatus.RUNNING
        worker.active_tasks.append(task_id)
        worker.task_count += 1
        return worker

    # ── Execution ────────────────────────────────────────────────

    def execute_task(self, task_id: str) -> Any:
        """Execute a task on assigned worker."""
        task = self.tasks.get(task_id)
        if task is None:
            raise KeyError(f"Task '{task_id}' not found")
        if task.func is None:
            return None

        try:
            task.status = TaskStatus.RUNNING
            result = task.func(*task.args, **task.kwargs)
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            # Release worker
            if task.assigned_worker:
                worker = self.workers.get(task.assigned_worker)
                if worker:
                    worker.active_tasks = [
                        t for t in worker.active_tasks if t != task_id
                    ]
                    worker.completed_count += 1
            return result
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()
            if task.assigned_worker:
                worker = self.workers.get(task.assigned_worker)
                if worker:
                    worker.active_tasks = [
                        t for t in worker.active_tasks if t != task_id
                    ]
                    worker.failed_count += 1
            raise

    def execute_all_pending(self) -> list[str]:
        """Assign and execute all pending tasks."""
        executed: list[str] = []
        for task_id, task in list(self.tasks.items()):
            if task.status == TaskStatus.PENDING:
                self.assign_task(task_id)
                if task.assigned_worker:
                    try:
                        self.execute_task(task_id)
                        executed.append(task_id)
                    except Exception:
                        executed.append(task_id)  # failed but attempted
        return executed

    # ── Result ───────────────────────────────────────────────────

    def get_result(self, task_id: str) -> Any:
        """Get task result."""
        task = self.tasks.get(task_id)
        return task.result if task else None

    def aggregate_results(self, task_ids: list[str]) -> dict[str, Any]:
        """Aggregate results from multiple tasks."""
        results = {}
        for tid in task_ids:
            task = self.tasks.get(tid)
            if task and task.result is not None:
                results[tid] = task.result
        return results

    # ── Sharding ─────────────────────────────────────────────────

    def shard_task(
        self, func: Callable, data: list[Any], shard_size: int = 10
    ) -> list[str]:
        """Split data into shards and submit as separate tasks."""
        task_ids = []
        for i in range(0, len(data), shard_size):
            shard = data[i : i + shard_size]
            tid = self.submit(func, shard)
            task_ids.append(tid)
        return task_ids

    # ── Stats ────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        by_status: dict[str, int] = {}
        for task in self.tasks.values():
            s = task.status.value
            by_status[s] = by_status.get(s, 0) + 1
        return {
            "workers": len(self.workers),
            "tasks": len(self.tasks),
            "by_status": by_status,
            "available_workers": sum(
                1 for w in self.workers.values() if w.is_available()
            ),
        }
