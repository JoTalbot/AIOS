"""Tests for aios_core/task_scheduler.py"""
from __future__ import annotations
import pytest
from aios_core.task_scheduler import TaskScheduler


@pytest.fixture()
def scheduler():
    return TaskScheduler()


class TestTaskScheduler:
    def test_create(self, scheduler):
        assert scheduler is not None

    def test_schedule(self, scheduler):
        result = scheduler.schedule(name="cleanup", func=lambda: "done", run_at="2099-01-01T00:00:00")
        assert result is not None

    def test_schedule_in(self, scheduler):
        result = scheduler.schedule_in(name="delayed", func=lambda: "ok", seconds=60)
        assert result is not None

    def test_schedule_recurring(self, scheduler):
        result = scheduler.schedule_recurring(name="periodic", func=lambda: "tick", interval_seconds=300)
        assert result is not None

    def test_cancel(self, scheduler):
        scheduler.schedule(name="cancel_me", func=lambda: "nope", run_at="2099-01-01T00:00:00")
        scheduler.cancel("cancel_me")

    def test_get_task(self, scheduler):
        scheduler.schedule(name="get_me", func=lambda: "ok", run_at="2099-01-01T00:00:00")
        task = scheduler.get_task("get_me")
        assert task is not None

    def test_get_pending(self, scheduler):
        scheduler.schedule(name="t1", func=lambda: "a", run_at="2099-01-01T00:00:00")
        scheduler.schedule(name="t2", func=lambda: "b", run_at="2099-01-01T00:00:00")
        pending = scheduler.get_pending()
        assert isinstance(pending, list)
        assert len(pending) >= 2

    def test_tick(self, scheduler):
        result = scheduler.tick()
        assert isinstance(result, (int, list, dict))

    def test_stats(self, scheduler):
        s = scheduler.stats()
        assert isinstance(s, dict)
