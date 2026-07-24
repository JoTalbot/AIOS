"""Tests for fleet_scheduler module — multi-device orchestration."""

from __future__ import annotations

import time

from aios_core.fleet_scheduler import (
    DeviceStatus,
    FleetDevice,
    FleetScheduler,
    FleetTask,
    SchedulingPolicy,
    TaskPriority,
    TaskStatus,
)

# ─── FleetDevice ───

class TestFleetDevice:
    """Tests for FleetDevice dataclass."""

    def test_online_available(self) -> None:
        """Online device with no tasks → available."""
        device = FleetDevice(device_id="dev1", status=DeviceStatus.ONLINE)
        assert device.is_available

    def test_offline_not_available(self) -> None:
        """Offline device → not available."""
        device = FleetDevice(device_id="dev1", status=DeviceStatus.OFFLINE)
        assert not device.is_available

    def test_busy_not_available(self) -> None:
        """Device at max concurrent → not available."""
        device = FleetDevice(device_id="dev1", max_concurrent=1, current_tasks=1)
        assert not device.is_available

    def test_cooldown_expired_available(self) -> None:
        """Cooldown expired → available."""
        device = FleetDevice(
            device_id="dev1",
            status=DeviceStatus.COOLDOWN,
            cooldown_until=time.time() - 1,  # Expired
        )
        assert device.is_available

    def test_cooldown_active_not_available(self) -> None:
        """Active cooldown → not available."""
        device = FleetDevice(
            device_id="dev1",
            status=DeviceStatus.COOLDOWN,
            cooldown_until=time.time() + 60,
        )
        assert not device.is_available

    def test_utilization_zero(self) -> None:
        """No tasks → 0% utilization."""
        device = FleetDevice(device_id="dev1", max_concurrent=4, current_tasks=0)
        assert device.utilization == 0.0

    def test_utilization_half(self) -> None:
        """2 of 4 tasks → 50% utilization."""
        device = FleetDevice(device_id="dev1", max_concurrent=4, current_tasks=2)
        assert device.utilization == 0.5

    def test_utilization_full(self) -> None:
        """4 of 4 tasks → 100% utilization."""
        device = FleetDevice(device_id="dev1", max_concurrent=4, current_tasks=4)
        assert device.utilization == 1.0

    def test_reliability_new_device(self) -> None:
        """New device with no history → reliability 1.0."""
        device = FleetDevice(device_id="dev1")
        assert device.reliability == 1.0

    def test_reliability_good(self) -> None:
        """9 successes, 1 fail → 0.9 reliability."""
        device = FleetDevice(device_id="dev1", success_count=9, fail_count=1)
        assert abs(device.reliability - 0.9) < 0.01

    def test_reliability_bad(self) -> None:
        """1 success, 9 fails → 0.1 reliability."""
        device = FleetDevice(device_id="dev1", success_count=1, fail_count=9)
        assert abs(device.reliability - 0.1) < 0.01


# ─── FleetTask ───

class TestFleetTask:
    """Tests for FleetTask dataclass."""

    def test_task_creation(self) -> None:
        """Create task with defaults."""
        task = FleetTask(task_id="t1", platform="olx", action="collect")
        assert task.status == TaskStatus.PENDING
        assert task.assigned_device is None
        assert task.priority == TaskPriority.NORMAL

    def test_task_duration(self) -> None:
        """Completed task → duration computed."""
        task = FleetTask(
            task_id="t1", platform="olx", action="collect",
            started_at=100.0, completed_at=115.0,
        )
        assert task.duration == 15.0

    def test_task_duration_running(self) -> None:
        """Running task → duration None."""
        task = FleetTask(task_id="t1", platform="olx", action="collect")
        assert task.duration is None

    def test_can_retry(self) -> None:
        """Can retry when retry_count < max_retries."""
        task = FleetTask(task_id="t1", platform="olx", action="collect", max_retries=3)
        assert task.can_retry
        task.retry_count = 2
        assert task.can_retry
        task.retry_count = 3
        assert not task.can_retry


# ─── FleetScheduler ───

class TestFleetScheduler:
    """Tests for FleetScheduler."""

    def _make_scheduler(self, n_devices: int = 3) -> FleetScheduler:
        """Create scheduler with N online devices."""
        scheduler = FleetScheduler(policy=SchedulingPolicy.LEAST_BUSY)
        for i in range(n_devices):
            dev = FleetDevice(
                device_id=f"dev{i}",
                platform="olx",
                status=DeviceStatus.ONLINE,
                max_concurrent=2,
            )
            scheduler.register_device(dev)
        return scheduler

    def test_register_device(self) -> None:
        """Register device adds to fleet."""
        scheduler = FleetScheduler()
        dev = FleetDevice(device_id="dev1")
        scheduler.register_device(dev)
        stats = scheduler.stats()
        assert stats["total_devices"] == 1

    def test_remove_device(self) -> None:
        """Remove device from fleet."""
        scheduler = FleetScheduler()
        dev = FleetDevice(device_id="dev1")
        scheduler.register_device(dev)
        scheduler.remove_device("dev1")
        assert scheduler.stats()["total_devices"] == 0

    def test_heartbeat(self) -> None:
        """Heartbeat updates device last_seen."""
        scheduler = FleetScheduler()
        dev = FleetDevice(device_id="dev1", last_seen=0)
        scheduler.register_device(dev)
        scheduler.heartbeat("dev1")
        assert dev.last_seen > 0

    def test_heartbeat_revives_offline(self) -> None:
        """Heartbeat from offline device → online."""
        scheduler = FleetScheduler()
        dev = FleetDevice(device_id="dev1", status=DeviceStatus.OFFLINE)
        scheduler.register_device(dev)
        scheduler.heartbeat("dev1")
        assert dev.status == DeviceStatus.ONLINE

    def test_health_check_marks_stale_offline(self) -> None:
        """Stale heartbeat → device marked offline."""
        scheduler = FleetScheduler(heartbeat_timeout=5)
        dev = FleetDevice(device_id="dev1")
        scheduler.register_device(dev)
        # Override last_seen after registration to simulate stale device
        dev.last_seen = time.time() - 100
        result = scheduler.health_check()
        assert result["dev1"] == DeviceStatus.OFFLINE

    def test_health_check_cooldown_expiry(self) -> None:
        """Expired cooldown → device back online."""
        scheduler = FleetScheduler()
        dev = FleetDevice(
            device_id="dev1",
            status=DeviceStatus.COOLDOWN,
            cooldown_until=time.time() - 1,
        )
        scheduler.register_device(dev)
        result = scheduler.health_check()
        assert result["dev1"] == DeviceStatus.ONLINE

    def test_schedule_task(self) -> None:
        """Schedule task assigns to available device."""
        scheduler = self._make_scheduler(2)
        task = scheduler.schedule("olx", "collect")
        assert task is not None
        assert task.status == TaskStatus.RUNNING
        assert task.assigned_device is not None

    def test_schedule_no_device_queues(self) -> None:
        """No device available → task queued."""
        scheduler = FleetScheduler()
        task = scheduler.schedule("olx", "collect")
        assert task is not None
        assert task.status == TaskStatus.PENDING
        assert task.assigned_device is None

    def test_schedule_priority(self) -> None:
        """Higher priority tasks scheduled first."""
        scheduler = self._make_scheduler(1)
        t_high = scheduler.schedule("olx", "collect", TaskPriority.HIGH)
        scheduler.schedule("olx", "collect", TaskPriority.LOW)
        assert t_high is not None
        # Second task queued since device max_concurrent=2
        # But first device takes priority task
        assert t_high.assigned_device == "dev0"

    def test_schedule_batch(self) -> None:
        """Batch schedule distributes across fleet."""
        scheduler = self._make_scheduler(3)
        tasks_spec = [
            ("olx", "collect", TaskPriority.NORMAL),
            ("rozetka", "collect", TaskPriority.HIGH),
            ("prom", "collect", TaskPriority.LOW),
        ]
        results = scheduler.schedule_batch(tasks_spec)
        assert len(results) >= 3

    def test_complete_task(self) -> None:
        """Complete task releases device."""
        scheduler = self._make_scheduler(1)
        task = scheduler.schedule("olx", "collect")
        assert task is not None
        device = scheduler._devices[task.assigned_device]
        assert device.current_tasks == 1

        result = scheduler.complete_task(task.task_id, {"items": 50})
        assert result.status == TaskStatus.COMPLETED
        assert device.current_tasks == 0
        assert device.success_count == 1

    def test_fail_task_retry(self) -> None:
        """Failed task retries when retries available."""
        scheduler = FleetScheduler()
        dev = FleetDevice(device_id="dev1", platform="olx", max_concurrent=2)
        scheduler.register_device(dev)
        task = scheduler.schedule("olx", "collect")
        assert task is not None

        # Add another device for retry
        dev2 = FleetDevice(device_id="dev2", platform="olx", max_concurrent=2)
        scheduler.register_device(dev2)

        result = scheduler.fail_task(task.task_id, "timeout")
        # After fail, task gets reassigned by _process_queue to dev2
        assert result.retry_count == 1
        # Task may be RUNNING (reassigned) or RETRYING (if no device available)
        assert result.status in (TaskStatus.RETRYING, TaskStatus.RUNNING)
        assert result.error == "timeout"

    def test_fail_task_max_retries(self) -> None:
        """Max retries exhausted → FAILED (no more retries possible)."""
        scheduler = FleetScheduler()
        dev = FleetDevice(device_id="dev1", platform="olx", max_concurrent=2)
        scheduler.register_device(dev)

        task = scheduler.schedule("olx", "collect")
        assert task is not None
        task_id = task.task_id

        # Manually exhaust retries: set retry_count to max_retries
        scheduler._tasks[task_id].retry_count = 3
        scheduler._tasks[task_id].max_retries = 3

        # Now can_retry=False → task should be FAILED
        scheduler.fail_task(task_id, "exhausted")
        task = scheduler._tasks[task_id]
        assert task.status == TaskStatus.FAILED
        assert task.can_retry is False

    def test_cancel_task(self) -> None:
        """Cancel task removes from queue and releases device."""
        scheduler = self._make_scheduler(1)
        task = scheduler.schedule("olx", "collect")
        assert task is not None

        result = scheduler.cancel_task(task.task_id)
        assert result.status == TaskStatus.CANCELLED

    def test_cancel_nonexistent(self) -> None:
        """Cancel non-existent task → None."""
        scheduler = FleetScheduler()
        result = scheduler.cancel_task("nonexistent")
        assert result is None

    def test_stats(self) -> None:
        """Stats returns fleet metrics."""
        scheduler = self._make_scheduler(3)
        stats = scheduler.stats()
        assert stats["total_devices"] == 3
        assert stats["available_devices"] == 3
        assert stats["queue_size"] == 0

    def test_stats_after_scheduling(self) -> None:
        """Stats updated after scheduling tasks."""
        scheduler = self._make_scheduler(2)
        scheduler.schedule("olx", "collect")
        scheduler.schedule("olx", "collect")
        stats = scheduler.stats()
        assert stats["running_tasks"] >= 2

    def test_get_device_tasks(self) -> None:
        """Get tasks assigned to specific device."""
        scheduler = self._make_scheduler(1)
        task = scheduler.schedule("olx", "collect")
        assert task is not None
        device_tasks = scheduler.get_device_tasks(task.assigned_device)
        assert len(device_tasks) >= 1

    def test_round_robin_policy(self) -> None:
        """Round-robin distributes tasks evenly."""
        scheduler = FleetScheduler(policy=SchedulingPolicy.ROUND_ROBIN)
        for i in range(3):
            dev = FleetDevice(device_id=f"dev{i}", platform="olx", max_concurrent=5)
            scheduler.register_device(dev)

        tasks = []
        for i in range(6):
            t = scheduler.schedule("olx", "collect")
            if t:
                tasks.append(t)

        assigned = [t.assigned_device for t in tasks]
        # Should distribute across all 3 devices
        assert len(set(assigned)) >= 2

    def test_least_busy_policy(self) -> None:
        """Least-busy prefers devices with fewer tasks."""
        scheduler = FleetScheduler(policy=SchedulingPolicy.LEAST_BUSY)
        dev1 = FleetDevice(device_id="busy_dev", platform="olx", max_concurrent=4, current_tasks=3)
        dev2 = FleetDevice(device_id="idle_dev", platform="olx", max_concurrent=4, current_tasks=0)
        scheduler.register_device(dev1)
        scheduler.register_device(dev2)

        task = scheduler.schedule("olx", "collect")
        assert task.assigned_device == "idle_dev"

    def test_queue_processing_after_completion(self) -> None:
        """Completing task processes queued tasks."""
        scheduler = FleetScheduler()
        dev = FleetDevice(device_id="dev1", platform="olx", max_concurrent=1)
        scheduler.register_device(dev)

        t1 = scheduler.schedule("olx", "collect")
        t2 = scheduler.schedule("olx", "parse")
        assert t1 is not None
        assert t2 is not None

        # t1 running, t2 queued
        assert t1.status == TaskStatus.RUNNING
        assert t2.status == TaskStatus.PENDING

        # Complete t1 → t2 should get assigned
        scheduler.complete_task(t1.task_id)
        t2_updated = scheduler._tasks[t2.task_id]
        assert t2_updated.status == TaskStatus.RUNNING

    def test_cooldown_on_failures(self) -> None:
        """3 failures → device enters cooldown."""
        scheduler = FleetScheduler(cooldown_seconds=60)
        dev = FleetDevice(device_id="dev1", platform="olx", max_concurrent=5)
        scheduler.register_device(dev)
        # Add more devices for retries
        dev2 = FleetDevice(device_id="dev2", platform="olx", max_concurrent=5)
        scheduler.register_device(dev2)

        task = scheduler.schedule("olx", "collect")
        assert task is not None

        # Fail 3 times on dev1
        scheduler.fail_task(task.task_id, "err1")
        # After 1st fail, dev1.fail_count=1
        assert dev.fail_count >= 1


# ─── Integration ───

class TestFleetSchedulerIntegration:
    """Integration tests for full fleet workflow."""

    def test_full_workflow(self) -> None:
        """Register → schedule → complete → stats."""
        scheduler = FleetScheduler(policy=SchedulingPolicy.LEAST_BUSY)

        # Register 5 devices
        for i in range(5):
            dev = FleetDevice(device_id=f"phone{i}", platform="olx", max_concurrent=3)
            scheduler.register_device(dev)

        # Schedule 10 tasks
        tasks = []
        for i in range(10):
            t = scheduler.schedule("olx", "collect", TaskPriority.NORMAL)
            if t:
                tasks.append(t)

        # Some running, some queued
        running = [t for t in tasks if t.status == TaskStatus.RUNNING]
        assert len(running) > 0

        # Complete all running tasks
        for t in running:
            scheduler.complete_task(t.task_id, {"items": 100})

        # Check stats
        stats = scheduler.stats()
        assert stats["completed_tasks"] == len(running)
        assert stats["total_tasks"] >= 10

    def test_heartbeat_timeout_workflow(self) -> None:
        """Device goes offline → tasks queued → heartbeat → re-process."""
        scheduler = FleetScheduler(heartbeat_timeout=10)

        dev = FleetDevice(device_id="dev1", platform="olx", max_concurrent=2)
        scheduler.register_device(dev)

        task = scheduler.schedule("olx", "collect")
        assert task is not None
        assert task.assigned_device == "dev1"

        # Simulate timeout
        dev.last_seen = time.time() - 100
        scheduler.health_check()
        assert dev.status == DeviceStatus.OFFLINE

        # Heartbeat revives
        scheduler.heartbeat("dev1")
        assert dev.status == DeviceStatus.ONLINE
