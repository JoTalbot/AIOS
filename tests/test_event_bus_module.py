"""Tests for aios_core/event_bus.py"""
from __future__ import annotations
import pytest
from aios_core.event_bus import EventBus
from aios_core.storage import Database


@pytest.fixture()
def db(tmp_path):
    db = Database(db_path=str(tmp_path / "test.db"))
    yield db
    db.close()


@pytest.fixture()
def bus(db):
    return EventBus(db)


class TestEventBus:
    def test_subscribe(self, bus):
        sub_id = bus.subscribe("user.created", lambda e: None)
        assert sub_id is not None

    def test_emit(self, bus):
        bus.subscribe("test.event", lambda e: None)
        event = bus.emit("test.event", source="test", data={"key": "val"})
        assert event is not None

    def test_emit_no_subscribers(self, bus):
        event = bus.emit("orphan.event", source="test", data={})
        assert event is not None

    def test_unsubscribe(self, bus):
        sub_id = bus.subscribe("temp", lambda e: None)
        bus.unsubscribe(sub_id)

    def test_query(self, bus):
        bus.emit("q.event", source="test", data={})
        results = bus.query()
        assert isinstance(results, list)

    def test_query_by_type(self, bus):
        bus.emit("type.a", source="test", data={})
        bus.emit("type.b", source="test", data={})
        results = bus.query(event_type="type.a")
        assert isinstance(results, list)

    def test_get_event(self, bus):
        event = bus.emit("get.me", source="test", data={})
        eid = getattr(event, 'event_id', getattr(event, 'id', None))
        if eid:
            fetched = bus.get_event(eid)
            assert fetched is not None

    def test_recent(self, bus):
        bus.emit("recent.event", source="test", data={})
        results = bus.recent()
        assert isinstance(results, list)

    def test_subscribe_pattern(self, bus):
        sub_id = bus.subscribe_pattern("user.*", lambda e: None)
        assert sub_id is not None

    def test_stats(self, bus):
        s = bus.stats()
        assert isinstance(s, dict)
