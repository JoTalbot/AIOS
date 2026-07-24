"""Distributed Task Queue for AIOS v10.5.0.

In-memory priority queue with task priorities, retry policies,
dead letter queue, worker assignment, progress tracking, and
task lifecycle management.

Classes:
    TaskPriority    — LOW / NORMAL / HIGH / CRITICAL
    TaskStatus      — QUEUED / RUNNING / COMPLETED / FAILED / RETRYING / DEAD
    Task            — full task definition with priority, retry, metadata
    Worker          — named worker with capacity tracking
    DistributedQueue — enhanced queue with priorities, retry, DLQ, workers
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────

class TaskPriority(int, Enum):
    """Task priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskStatus(str, Enum):
    """Task lifecycle status."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD = "dead"  # in dead letter queue


# ── Task ─────────────────────────────────────────────────────────────────────

@dataclass
class Task:
    """Full task definition."""
    id: str = ""
    name: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.QUEUED
    max_retries: int = 3
    retry_count: int = 0
    worker_id: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    result: Any = None

    def __post_init__(self) -> None:
        if not self.id:
            import uuid
            self.id = str(uuid.uuid4())[:8]

    def duration(self) -> float:
        """Return execution duration."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return 0.0

    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.retry_count < self.max_retries


# ── Worker ───────────────────────────────────────────────────────────────────

@dataclass
class Worker:
    """Named worker with capacity and assignment tracking."""
    id: str
    capacity: int = 10  # max concurrent tasks
    assigned_tasks: list[str] = field(default_factory=list)
    completed_tasks: int = 0
    failed_tasks: int = 0

    def available_capacity(self) -> int:
        """Return remaining capacity."""
        return self.capacity - len(self.assigned_tasks)

    def is_available(self) -> bool:
        """Check if worker has capacity."""
        return self.available_capacity() > 0


# ── Distributed Queue ────────────────────────────────────────────────────────

class DistributedQueue:
    """Enhanced in-memory priority queue with retry, DLQ, workers.

    Features:
    - Priority-based ordering (CRITICAL first)
    - Worker assignment with capacity tracking
    - Retry policy per task
    - Dead letter queue for permanently failed tasks
    - Progress tracking and metrics
    """

    def __init__(self) -> None:
        self._queue: list[Task] = []
        self._running: dict[str, Task] = {}   # task_id → Task
        self._completed: list[Task] = []
        self._dead_letter: list[Task] = []
        self._workers: dict[str, Worker] = {}
        self._task_map: dict[str, Task] = {}

    # ── Enqueue ──────────────────────────────────────────────────

    def enqueue(self, payload: dict[str, Any], name: str = "",
                priority: TaskPriority = TaskPriority.NORMAL,
                max_retries: int = 3) -> Task:
        """Enqueue a new task with priority."""
        task = Task(name=name, payload=payload, priority=priority, max_retries=max_retries)
        self._queue.append(task)
        self._task_map[task.id] = task
        # Sort queue by priority (highest first)
        self._queue.sort(key=lambda t: t.priority, reverse=True)
        logger.info("Enqueued task '%s' (priority=%s)", task.id, priority.name)
        return task

    # ── Dequeue ──────────────────────────────────────────────────

    def dequeue(self) -> Task | None:
        """Dequeue highest-priority task and assign to available worker."""
        if not self._queue:
            return None

        # Find available worker
        worker = self._find_available_worker()
        task = self._queue.pop(0)
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()

        if worker:
            task.worker_id = worker.id
            worker.assigned_tasks.append(task.id)

        self._running[task.id] = task
        return task

    # ── Complete ─────────────────────────────────────────────────

    def complete(self, task_id: str, result: Any = None) -> None:
        """Mark a task as completed."""
        task = self._task_map.get(task_id)
        if task is None:
            raise KeyError(f"Task '{task_id}' not found")
        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()
        task.result = result
        self._running.pop(task_id, None)
        self._completed.append(task)

        # Release worker capacity
        if task.worker_id:
            worker = self._workers.get(task.worker_id)
            if worker:
                worker.assigned_tasks = [t for t in worker.assigned_tasks if t != task_id]
                worker.completed_tasks += 1

    def fail(self, task_id: str, error: str = "") -> None:
        """Mark a task as failed. Retry or move to DLQ."""
        task = self._task_map.get(task_id)
        if task is None:
            raise KeyError(f"Task '{task_id}' not found")

        task.error = error
        self._running.pop(task_id, None)

        # Release worker
        if task.worker_id:
            worker = self._workers.get(task.worker_id)
            if worker:
                worker.assigned_tasks = [t for t in worker.assigned_tasks if t != task_id]
                worker.failed_tasks += 1

        if task.can_retry():
            task.retry_count += 1
            task.status = TaskStatus.RETRYING
            task.worker_id = ""
            self._queue.append(task)
            self._queue.sort(key=lambda t: t.priority, reverse=True)
        else:
            task.status = TaskStatus.DEAD
            self._dead_letter.append(task)

    # ── Workers ──────────────────────────────────────────────────

    def register_worker(self, worker_id: str, capacity: int = 10) -> Worker:
        """Register a worker with capacity."""
        worker = Worker(id=worker_id, capacity=capacity)
        self._workers[worker_id] = worker
        return worker

    def unregister_worker(self, worker_id: str) -> None:
        """Remove a worker."""
        del self._workers[worker_id]

    def _find_available_worker(self) -> Worker | None:
        """Find worker with available capacity."""
        for worker in self._workers.values():
            if worker.is_available():
                return worker
        return None

    # ── Dead Letter Queue ────────────────────────────────────────

    def get_dead_letter_tasks(self) -> list[Task]:
        """Return tasks in the dead letter queue."""
        return self._dead_letter.copy()

    def retry_dead_letter(self, task_id: str) -> bool:
        """Retry a task from the dead letter queue."""
        for task in self._dead_letter:
            if task.id == task_id:
                task.status = TaskStatus.QUEUED
                task.retry_count = 0
                task.error = None
                self._dead_letter.remove(task)
                self._queue.append(task)
                self._queue.sort(key=lambda t: t.priority, reverse=True)
                return True
        return False

    def purge_dead_letter(self) -> int:
        """Remove all tasks from DLQ. Returns count purged."""
        count = len(self._dead_letter)
        self._dead_letter.clear()
        return count

    # ── Queries ──────────────────────────────────────────────────

    def size(self) -> int:
        """Return number of tasks in queue."""
        return len(self._queue)

    def running_count(self) -> int:
        """Return number of running tasks."""
        return len(self._running)

    def completed_count(self) -> int:
        """Return number of completed tasks."""
        return len(self._completed)

    def dead_letter_count(self) -> int:
        """Return number of dead letter tasks."""
        return len(self._dead_letter)

    def get_task(self, task_id: str) -> Task | None:
        """Return task by ID."""
        return self._task_map.get(task_id)

    # ── Stats ────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "queue_size": self.size(),
            "running": self.running_count(),
            "completed": self.completed_count(),
            "dead_letter": self.dead_letter_count(),
            "workers": len(self._workers),
            "total_tasks": len(self._task_map),
        }
