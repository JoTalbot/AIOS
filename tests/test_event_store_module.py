"""Tests for aios_core/event_store.py"""
from __future__ import annotations
import pytest
from aios_core.event_store import EventStore


@pytest.fixture()
def store():
    return EventStore()


class TestEventStore:
    def test_append(self, store):
        event = store.append(event_type="user.created", data={"user_id": "u1"})
        assert event is not None

    def test_get_events(self, store):
        store.append(event_type="e1", data={})
        store.append(event_type="e2", data={})
        events = store.get_events()
        assert isinstance(events, list)
        assert len(events) >= 2

    def test_get_event_by_id(self, store):
        event = store.append(event_type="e1", data={"key": "val"})
        eid = getattr(event, 'event_id', getattr(event, 'id', None))
        if eid:
            fetched = store.get_event_by_id(eid)
            assert fetched is not None

    def test_replay_all(self, store):
        store.append(event_type="e1", data={})
        store.append(event_type="e2", data={})
        result = store.replay_all()
        assert isinstance(result, (list, dict))

    def test_create_snapshot(self, store):
        store.append(event_type="e1", data={}, aggregate_id="agg1")
        snap = store.create_snapshot(aggregate_id="agg1")
        assert snap is not None

    def test_stats(self, store):
        store.append(event_type="e1", data={})
        s = store.stats()
        assert isinstance(s, dict)
