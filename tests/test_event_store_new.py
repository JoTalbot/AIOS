"""event_store test."""
def test(): from aios_core.event_store import EventStore; s = EventStore().stats(); assert isinstance(s, dict)
