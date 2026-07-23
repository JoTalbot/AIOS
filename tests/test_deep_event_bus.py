"""Deep event bus — handler isolation."""
from aios_core.event_bus import EventBus
def test_handler_failure_isolation():
    eb = EventBus()
    good = []
    def bad_handler(p): raise RuntimeError("fail")
    def good_handler(p): good.append(p)
    eb.on("test", bad_handler)
    eb.on("test", good_handler)
    eb.emit("test", {"x": 1})
    assert len(good) == 1
def test_no_handler_no_error():
    eb = EventBus()
    eb.emit("nonexistent", {})
    assert True
