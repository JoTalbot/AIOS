"""Task Scheduler for AIOS v10.6.0.

Enhanced in-memory scheduler with recurring tasks, cron-like scheduling,
task priorities, cancellation, history, and configurable tick intervals.

Classes:
    TaskPriority    — LOW / NORMAL / HIGH / CRITICAL
    ScheduledTask   — full task definition with scheduling metadata
    TaskScheduler   — enhanced scheduler with recurring, priority, history
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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


class TaskScheduleStatus(str, Enum):
    """Task lifecycle status."""
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Scheduled Task ───────────────────────────────────────────────────────────

@dataclass
class ScheduledTask:
    """Full task definition with scheduling metadata."""
    name: str
    func: Callable
    run_at: datetime
    kwargs: dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    recurring_interval: Optional[timedelta] = None
    max_retries: int = 0
    retry_count: int = 0
    status: TaskScheduleStatus = TaskScheduleStatus.SCHEDULED
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_run_at: Optional[float] = None

    def is_recurring(self) -> bool:
        """Check if task is recurring."""
        return self.recurring_interval is not None

    def next_run_time(self) -> Optional[datetime]:
        """Calculate next run time for recurring task."""
        if self.recurring_interval is None:
            return None
        base = self.run_at
        if self.last_run_at:
            base = datetime.fromtimestamp(self.last_run_at) + self.recurring_interval
        return base

    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.retry_count < self.max_retries


# ── Task Scheduler ──────────────────────────────────────────────────────────

class TaskScheduler:
    """Enhanced task scheduler with recurring, priority, history.

    Features:
    - One-time and recurring task scheduling
    - Priority-based execution order
    - Task cancellation
    - Retry policy per task
    - Tick-based execution loop
    - Execution history tracking
    """

    def __init__(self) -> None:
        self.tasks: dict[str, ScheduledTask] = {}
        self.history: list[dict[str, Any]] = []

    # ── Scheduling ──────────────────────────────────────────────

    def schedule(self, name: str, func: Callable, run_at: datetime, **kwargs: Any) -> ScheduledTask:
        """Schedule a task at a specific time."""
        task = ScheduledTask(name=name, func=func, run_at=run_at, kwargs=kwargs)
        self.tasks[name] = task
        return task

    def schedule_in(self, name: str, func: Callable, seconds: int, **kwargs: Any) -> ScheduledTask:
        """Schedule a task N seconds from now."""
        run_at = datetime.now() + timedelta(seconds=seconds)
        return self.schedule(name, func, run_at, **kwargs)

    def schedule_recurring(self, name: str, func: Callable, interval_seconds: int,
                           start_at: datetime | None = None, **kwargs: Any) -> ScheduledTask:
        """Schedule a recurring task with interval."""
        run_at = start_at or datetime.now() + timedelta(seconds=interval_seconds)
        task = ScheduledTask(
            name=name, func=func, run_at=run_at,
            recurring_interval=timedelta(seconds=interval_seconds),
            kwargs=kwargs,
        )
        self.tasks[name] = task
        return task

    def schedule_with_priority(self, name: str, func: Callable, run_at: datetime,
                               priority: TaskPriority = TaskPriority.NORMAL, **kwargs: Any) -> ScheduledTask:
        """Schedule a task with priority."""
        task = ScheduledTask(name=name, func=func, run_at=run_at, kwargs=kwargs, priority=priority)
        self.tasks[name] = task
        return task

    def schedule_with_retry(self, name: str, func: Callable, run_at: datetime,
                            max_retries: int = 3, **kwargs: Any) -> ScheduledTask:
        """Schedule a task with retry policy."""
        task = ScheduledTask(name=name, func=func, run_at=run_at, max_retries=max_retries, kwargs=kwargs)
        self.tasks[name] = task
        return task

    # ── Cancellation ────────────────────────────────────────────

    def cancel(self, name: str) -> None:
        """Cancel a scheduled task."""
        task = self.tasks.get(name)
        if task is None:
            raise KeyError(f"Task '{name}' not found")
        task.status = TaskScheduleStatus.CANCELLED

    def cancel_all(self) -> int:
        """Cancel all scheduled tasks."""
        count = 0
        for task in self.tasks.values():
            if task.status == TaskScheduleStatus.SCHEDULED:
                task.status = TaskScheduleStatus.CANCELLED
                count += 1
        return count

    # ── Execution ───────────────────────────────────────────────

    def tick(self) -> list[str]:
        """Execute all due tasks. Returns list of executed task names.

        Processes tasks in priority order (CRITICAL first).
        Recurring tasks are rescheduled after successful execution.
        """
        now = datetime.now()
        executed: list[str] = []

        # Sort by priority (highest first)
        due_tasks = sorted(
            [t for t in self.tasks.values()
             if t.status == TaskScheduleStatus.SCHEDULED and now >= t.run_at],
            key=lambda t: t.priority,
            reverse=True,
        )

        for task in due_tasks:
            task.status = TaskScheduleStatus.RUNNING
            task.last_run_at = time.time()

            try:
                task.result = task.func(**task.kwargs)
                task.status = TaskScheduleStatus.COMPLETED
                executed.append(task.name)
                self.history.append({
                    "name": task.name, "status": "completed",
                    "timestamp": time.time(), "result": task.result,
                })

                # Reschedule recurring task
                if task.is_recurring():
                    next_time = task.next_run_time()
                    if next_time:
                        task.run_at = next_time
                        task.status = TaskScheduleStatus.SCHEDULED
                        task.retry_count = 0
                    else:
                        task.status = TaskScheduleStatus.COMPLETED

            except Exception as e:
                task.error = str(e)
                task.retry_count += 1

                if task.can_retry():
                    task.status = TaskScheduleStatus.SCHEDULED
                    self.history.append({
                        "name": task.name, "status": "retrying",
                        "timestamp": time.time(), "error": str(e),
                        "retry_count": task.retry_count,
                    })
                else:
                    task.status = TaskScheduleStatus.FAILED
                    self.history.append({
                        "name": task.name, "status": "failed",
                        "timestamp": time.time(), "error": str(e),
                    })

        return executed

    # ── Queries ─────────────────────────────────────────────────

    def get_task(self, name: str) -> ScheduledTask | None:
        """Return task by name."""
        return self.tasks.get(name)

    def get_pending(self) -> list[ScheduledTask]:
        """Return all scheduled (pending) tasks."""
        return [t for t in self.tasks.values() if t.status == TaskScheduleStatus.SCHEDULED]

    def get_completed(self) -> list[ScheduledTask]:
        """Return all completed tasks."""
        return [t for t in self.tasks.values() if t.status == TaskScheduleStatus.COMPLETED]

    def get_failed(self) -> list[ScheduledTask]:
        """Return all failed tasks."""
        return [t for t in self.tasks.values() if t.status == TaskScheduleStatus.FAILED]

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return execution history."""
        return self.history[-limit:]

    # ── Stats ───────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        by_status: dict[str, int] = {}
        for task in self.tasks.values():
            s = task.status.value
            by_status[s] = by_status.get(s, 0) + 1
        return {
            "total": len(self.tasks),
            "by_status": by_status,
            "history_size": len(self.history),
            "recurring_tasks": sum(1 for t in self.tasks.values() if t.is_recurring()),
        }


scheduler = TaskScheduler()
