"""Tests for aios_core/digital_twin.py"""
from __future__ import annotations
import pytest
from aios_core.digital_twin import DigitalTwin


@pytest.fixture()
def twin():
    return DigitalTwin(twin_id="t1", real_entity="server-1")


class TestDigitalTwin:
    def test_create(self, twin):
        assert twin.twin_id == "t1"

    def test_add_property(self, twin):
        twin.add_property("cpu_usage", 0.45)
        assert twin.get_property("cpu_usage") == 0.45

    def test_update_property(self, twin):
        twin.add_property("mem", 100)
        twin.update_property("mem", 200)
        assert twin.get_property("mem") == 200

    def test_get_property_nonexistent(self, twin):
        assert twin.get_property("nope") is None

    def test_sync(self, twin):
        twin.add_property("status", "running")
        twin.sync(new_state={"status": "stopped", "load": 0.1})

    def test_rollback(self, twin):
        twin.add_property("v", 1)
        twin.update_property("v", 2)
        twin.rollback()

    def test_get_history(self, twin):
        twin.add_property("x", 1)
        history = twin.get_history()
        assert isinstance(history, list)

    def test_get_state(self, twin):
        twin.add_property("a", 1)
        state = twin.get_state()
        assert isinstance(state, dict)

    def test_stats(self, twin):
        s = twin.stats()
        assert isinstance(s, dict)
