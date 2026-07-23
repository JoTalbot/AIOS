"""event_store standalone test."""
from aios_core.event_store import EventStore
def test_init(): s = EventStore().stats(); assert isinstance(s, dict)
