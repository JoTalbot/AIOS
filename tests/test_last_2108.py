"""Last batch 8."""
from aios_core.storage import Database
from aios_core.knowledge_graph import KnowledgeGraph
from aios_core.event_bus import EventBus
from aios_core.rate_limiter import RateLimiter
def test():
    assert Database(":memory:").stats() is not None
    assert KnowledgeGraph().stats() is not None
    eb = EventBus(); eb.on("t", lambda p: None); eb.emit("t", {})
    assert RateLimiter().is_allowed("k") is True
