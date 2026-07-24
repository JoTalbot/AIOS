"""Fleet scheduler — multi-device orchestration for parallel scraping.

Manages a fleet of Android devices (or virtual workers) for:
- Task distribution across devices (round-robin, priority-based)
- Device health monitoring (online/offline/busy)
- Parallel execution coordination with task queues
- Automatic retry on failed devices
- Load balancing and throttling

Designed for headless scraping fleets on multiple phones/tablets.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DeviceStatus(Enum):
    """Status of a fleet device."""

    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"
    COOLDOWN = "cooldown"


class TaskPriority(Enum):
    """Priority levels for fleet tasks."""

    CRITICAL = 0  # Immediate execution
    HIGH = 1  # Next available device
    NORMAL = 2  # Standard queue
    LOW = 3  # Background / batch
    MAINTENANCE = 4  # Device maintenance tasks


class TaskStatus(Enum):
    """Status of a scheduled task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class SchedulingPolicy(Enum):
    """Task scheduling distribution policy."""

    ROUND_ROBIN = "round_robin"
    LEAST_BUSY = "least_busy"
    PRIORITY_FIRST = "priority_first"
    RANDOM = "random"


@dataclass
class FleetDevice:
    """A device in the scraping fleet."""

    device_id: str
    platform: str = ""  # e.g. "olx", "rozetka"
    status: DeviceStatus = DeviceStatus.ONLINE
    max_concurrent: int = 1  # Max simultaneous tasks
    current_tasks: int = 0  # Currently running tasks
    success_count: int = 0  # Completed tasks
    fail_count: int = 0  # Failed tasks
    last_seen: float = 0.0  # Timestamp of last heartbeat
    cooldown_until: float = 0.0  # Resume after cooldown
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_available(self) -> bool:
        """True if device can accept new tasks."""
        if self.status == DeviceStatus.COOLDOWN:
            return time.time() >= self.cooldown_until
        return (
            self.status == DeviceStatus.ONLINE
            and self.current_tasks < self.max_concurrent
        )

    @property
    def utilization(self) -> float:
        """Current utilization ratio (0.0 to 1.0)."""
        if self.max_concurrent == 0:
            return 1.0
        return self.current_tasks / self.max_concurrent

    @property
    def reliability(self) -> float:
        """Reliability score based on success/fail ratio (0.0 to 1.0)."""
        total = self.success_count + self.fail_count
        if total == 0:
            return 1.0  # New device assumed reliable
        return self.success_count / total


@dataclass
class FleetTask:
    """A task to be executed on a fleet device."""

    task_id: str
    platform: str  # Target platform
    action: str  # e.g. "collect", "parse", "monitor"
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    assigned_device: str | None = None
    max_retries: int = 3
    retry_count: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    params: dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float | None:
        """Task execution duration in seconds."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    @property
    def can_retry(self) -> bool:
        """True if task can be retried."""
        return self.retry_count < self.max_retries


class FleetScheduler:
    """Multi-device fleet scheduler for parallel scraping.

    Provides:
    - register_device() / remove_device() — fleet management
    - schedule() — distribute task to best available device
    - schedule_batch() — distribute multiple tasks
    - complete_task() / fail_task() — task lifecycle
    - health_check() — device health monitoring
    - stats() — fleet statistics and utilization metrics
    """

    def __init__(
        self,
        policy: SchedulingPolicy = SchedulingPolicy.LEAST_BUSY,
        default_max_retries: int = 3,
        cooldown_seconds: float = 30.0,
        heartbeat_timeout: float = 120.0,
    ) -> None:
        """Initialize FleetScheduler.

        Args:
            policy: Default scheduling policy.
            default_max_retries: Default max retries for tasks.
            cooldown_seconds: Cooldown period after device failures.
            heartbeat_timeout: Seconds before device marked offline.
        """
        self.policy = policy
        self.default_max_retries = default_max_retries
        self.cooldown_seconds = cooldown_seconds
        self.heartbeat_timeout = heartbeat_timeout
        self._devices: dict[str, FleetDevice] = {}
        self._tasks: dict[str, FleetTask] = {}
        self._queue: list[str] = []  # Pending task IDs (ordered)
        self._rr_index: int = 0  # Round-robin index
        self._counter: int = 0  # Task ID counter

    def _next_task_id(self) -> str:
        """Generate unique task ID."""
        self._counter += 1
        return f"task_{self._counter}"

    def register_device(self, device: FleetDevice) -> None:
        """Register a device in the fleet.

        Args:
            device: FleetDevice to register.
        """
        device.last_seen = time.time()
        self._devices[device.device_id] = device

    def remove_device(self, device_id: str) -> None:
        """Remove a device from the fleet.

        Args:
            device_id: Device ID to remove.
        """
        self._devices.pop(device_id, None)

    def heartbeat(self, device_id: str) -> None:
        """Record device heartbeat to keep it online.

        Args:
            device_id: Device sending heartbeat.
        """
        device = self._devices.get(device_id)
        if device:
            device.last_seen = time.time()
            if device.status in (DeviceStatus.OFFLINE, DeviceStatus.ERROR):
                device.status = DeviceStatus.ONLINE

    def health_check(self) -> dict[str, DeviceStatus]:
        """Check all devices and mark stale ones as offline.

        Returns:
            Dict of device_id → current DeviceStatus.
        """
        now = time.time()
        result: dict[str, DeviceStatus] = {}

        for device_id, device in self._devices.items():
            # Check cooldown expiry
            if device.status == DeviceStatus.COOLDOWN:
                if now >= device.cooldown_until:
                    device.status = DeviceStatus.ONLINE
                    device.current_tasks = 0

            # Check heartbeat timeout
            if device.status == DeviceStatus.ONLINE:
                if now - device.last_seen > self.heartbeat_timeout:
                    device.status = DeviceStatus.OFFLINE

            result[device_id] = device.status

        return result

    def _available_devices(self, platform: str | None = None) -> list[FleetDevice]:
        """Get list of available devices, optionally filtered by platform.

        Args:
            platform: Filter by platform (None = all available).

        Returns:
            List of available FleetDevice instances.
        """
        devices = []
        for device in self._devices.values():
            if not device.is_available:
                continue
            if platform and device.platform and device.platform != platform:
                continue
            devices.append(device)
        return devices

    def _select_device(
        self,
        devices: list[FleetDevice],
        policy: SchedulingPolicy | None = None,
    ) -> FleetDevice | None:
        """Select best device according to scheduling policy.

        Args:
            devices: Available devices to choose from.
            policy: Scheduling policy override.

        Returns:
            Selected FleetDevice or None if no devices available.
        """
        if not devices:
            return None

        effective_policy = policy or self.policy

        if effective_policy == SchedulingPolicy.ROUND_ROBIN:
            idx = self._rr_index % len(devices)
            self._rr_index += 1
            return devices[idx]

        elif effective_policy == SchedulingPolicy.LEAST_BUSY:
            # Sort by utilization ascending, then reliability descending
            sorted_devs = sorted(
                devices,
                key=lambda d: (-d.reliability, d.utilization),
            )
            return sorted_devs[0]

        elif effective_policy == SchedulingPolicy.PRIORITY_FIRST:
            # Same as least_busy for device selection
            return min(devices, key=lambda d: d.utilization)

        elif effective_policy == SchedulingPolicy.RANDOM:
            import random

            return random.choice(devices)

        return devices[0]

    def schedule(
        self,
        platform: str,
        action: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        params: dict[str, Any] | None = None,
        policy: SchedulingPolicy | None = None,
    ) -> FleetTask | None:
        """Schedule a single task on the fleet.

        Args:
            platform: Target platform (e.g. "olx", "rozetka").
            action: Task action (e.g. "collect", "parse").
            priority: Task priority.
            params: Additional task parameters.
            policy: Scheduling policy override.

        Returns:
            Scheduled FleetTask or None if no device available.
        """
        task_id = self._next_task_id()
        task = FleetTask(
            task_id=task_id,
            platform=platform,
            action=action,
            priority=priority,
            max_retries=self.default_max_retries,
            params=params or {},
        )

        devices = self._available_devices(platform)
        device = self._select_device(devices, policy)

        if not device:
            # No device available — queue the task
            self._tasks[task_id] = task
            self._queue.append(task_id)
            return task

        # Assign to device
        task.assigned_device = device.device_id
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        device.current_tasks += 1

        self._tasks[task_id] = task
        return task

    def schedule_batch(
        self,
        tasks: list[tuple[str, str, TaskPriority]],
        policy: SchedulingPolicy | None = None,
    ) -> list[FleetTask]:
        """Schedule a batch of tasks across the fleet.

        Args:
            tasks: List of (platform, action, priority) tuples.
            policy: Scheduling policy override.

        Returns:
            List of FleetTask (some may be queued if no devices).
        """
        # Sort by priority (lower value = higher priority)
        sorted_tasks = sorted(
            tasks, key=lambda t: t[2].value if isinstance(t[2], TaskPriority) else 2
        )
        results = []
        for platform, action, priority in sorted_tasks:
            task = self.schedule(platform, action, priority, policy=policy)
            if task:
                results.append(task)
        return results

    def complete_task(
        self, task_id: str, result: dict[str, Any] | None = None
    ) -> FleetTask | None:
        """Mark a task as completed and release the device.

        Args:
            task_id: Task ID to complete.
            result: Optional result data.

        Returns:
            Updated FleetTask or None if task not found.
        """
        task = self._tasks.get(task_id)
        if not task:
            return None

        task.status = TaskStatus.COMPLETED
        task.completed_at = time.time()
        task.result = result

        # Release device
        if task.assigned_device:
            device = self._devices.get(task.assigned_device)
            if device:
                device.current_tasks = max(0, device.current_tasks - 1)
                device.success_count += 1

        # Check queue for pending tasks
        self._process_queue()

        return task

    def fail_task(self, task_id: str, error: str = "") -> FleetTask | None:
        """Mark a task as failed, retry or cooldown device.

        Args:
            task_id: Task ID that failed.
            error: Error message.

        Returns:
            Updated FleetTask or None if task not found.
        """
        task = self._tasks.get(task_id)
        if not task:
            return None

        # Release device
        if task.assigned_device:
            device = self._devices.get(task.assigned_device)
            if device:
                device.current_tasks = max(0, device.current_tasks - 1)
                device.fail_count += 1
                # Put device in cooldown after failures
                if device.fail_count >= 3:
                    device.status = DeviceStatus.COOLDOWN
                    device.cooldown_until = time.time() + self.cooldown_seconds

        # Retry or mark failed
        if task.can_retry:
            task.retry_count += 1
            task.status = TaskStatus.RETRYING
            task.assigned_device = None
            task.error = error
            # Re-queue for retry
            self._queue.append(task_id)
            self._process_queue()
        else:
            task.status = TaskStatus.FAILED
            task.error = error

        return task

    def cancel_task(self, task_id: str) -> FleetTask | None:
        """Cancel a pending or running task.

        Args:
            task_id: Task ID to cancel.

        Returns:
            Cancelled FleetTask or None if not found.
        """
        task = self._tasks.get(task_id)
        if not task:
            return None

        # Release device if running
        if task.assigned_device:
            device = self._devices.get(task.assigned_device)
            if device:
                device.current_tasks = max(0, device.current_tasks - 1)

        task.status = TaskStatus.CANCELLED

        # Remove from queue if pending
        self._queue = [tid for tid in self._queue if tid != task_id]

        return task

    def _process_queue(self) -> None:
        """Try to assign queued tasks to available devices."""
        remaining: list[str] = []

        for task_id in self._queue:
            task = self._tasks.get(task_id)
            if not task or task.status == TaskStatus.CANCELLED:
                continue

            devices = self._available_devices(task.platform)
            device = self._select_device(devices)

            if device:
                task.assigned_device = device.device_id
                task.status = TaskStatus.RUNNING
                task.started_at = time.time()
                device.current_tasks += 1
            else:
                remaining.append(task_id)

        self._queue = remaining

    def stats(self) -> dict[str, Any]:
        """Compute fleet statistics.

        Returns:
            Dict with fleet metrics: total_devices, available, busy,
            utilization, queue_size, completed_tasks, failed_tasks.
        """
        total = len(self._devices)
        available = sum(1 for d in self._devices.values() if d.is_available)
        busy = sum(
            1
            for d in self._devices.values()
            if d.status == DeviceStatus.BUSY
            or (d.status == DeviceStatus.ONLINE and d.current_tasks > 0)
        )

        avg_utilization = (
            sum(d.utilization for d in self._devices.values()) / total
            if total > 0
            else 0.0
        )

        avg_reliability = (
            sum(d.reliability for d in self._devices.values()) / total
            if total > 0
            else 0.0
        )

        completed = sum(
            1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED
        )
        failed = sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED)
        running = sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING)
        pending = len(self._queue)

        return {
            "total_devices": total,
            "available_devices": available,
            "busy_devices": busy,
            "offline_devices": sum(
                1 for d in self._devices.values() if d.status == DeviceStatus.OFFLINE
            ),
            "cooldown_devices": sum(
                1 for d in self._devices.values() if d.status == DeviceStatus.COOLDOWN
            ),
            "avg_utilization": round(avg_utilization, 3),
            "avg_reliability": round(avg_reliability, 3),
            "queue_size": pending,
            "running_tasks": running,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "total_tasks": len(self._tasks),
        }

    def get_device_tasks(self, device_id: str) -> list[FleetTask]:
        """Get all tasks assigned to a specific device.

        Args:
            device_id: Device ID.

        Returns:
            List of FleetTask assigned to this device.
        """
        return [
            t
            for t in self._tasks.values()
            if t.assigned_device == device_id and t.status == TaskStatus.RUNNING
        ]

    def rebalance(self) -> int:
        """Rebalance tasks from overloaded to underloaded devices.

        Moves tasks from devices with >80% utilization to devices with <30%.

        Returns:
            Number of tasks moved.
        """
        moved = 0
        overloaded = [
            d for d in self._devices.values() if d.utilization > 0.8 and d.is_available
        ]
        underloaded = [
            d for d in self._devices.values() if d.utilization < 0.3 and d.is_available
        ]

        for busy_device in overloaded:
            tasks = self.get_device_tasks(busy_device.device_id)
            for task in tasks:
                if underloaded:
                    target = min(underloaded, key=lambda d: d.utilization)
                    # Move task
                    task.assigned_device = target.device_id
                    busy_device.current_tasks = max(0, busy_device.current_tasks - 1)
                    target.current_tasks += 1
                    moved += 1

                    # Refresh underloaded list
                    underloaded = [
                        d
                        for d in self._devices.values()
                        if (d.utilization < 0.3
                        and d.is_available
                        and d.device_id != target.device_id)
                        or (d.device_id == target.device_id and d.utilization < 0.3)
                    ]

        return moved
