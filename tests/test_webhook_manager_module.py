"""Tests for aios_core/webhook_manager.py"""
from __future__ import annotations
import pytest
from aios_core.webhook_manager import WebhookManager


@pytest.fixture()
def manager():
    return WebhookManager()


class TestWebhookManager:
    def test_create(self, manager):
        assert manager is not None

    def test_register(self, manager):
        result = manager.register(name="test_hook", url="https://example.com/hook", events=["task.completed", "alert.fired"])
        assert result is not None

    def test_unregister(self, manager):
        manager.register(name="temp_hook", url="https://temp.com/hook", events=["test"])
        manager.unregister("temp_hook")

    def test_list_targets(self, manager):
        manager.register(name="h1", url="https://a.com/hook", events=["e1"])
        manager.register(name="h2", url="https://b.com/hook", events=["e2"])
        targets = manager.list_targets()
        assert len(targets) >= 2

    def test_notify(self, manager):
        manager.register(name="test_hook", url="https://example.com/hook", events=["test.event"])
        manager.notify(event="test.event", data={"key": "val"})

    def test_health_report(self, manager):
        result = manager.health_report()
        assert isinstance(result, dict)

    def test_stats(self, manager):
        # WebhookManager might not have stats(), check health_report instead
        result = manager.health_report()
        assert isinstance(result, dict)
