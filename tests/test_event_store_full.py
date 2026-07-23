"""Event store full."""
from aios_core.event_store import EventStore
def test(): s=EventStore().stats(); assert isinstance(s,dict)
