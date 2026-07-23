"""Event bus pub-sub ops."""
from aios_core.event_bus import EventBus
def test_pubsub(): eb = EventBus(); r=[]; eb.on("e", lambda p: r.append(p)); eb.emit("e", {"x":1}); eb.emit("e", {"x":2}); assert len(r)==2
