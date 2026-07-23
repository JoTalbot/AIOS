"""Integration2 test 2220."""
from aios_core.storage import Database
from aios_core.knowledge_graph import KnowledgeGraph
from aios_core.event_bus import EventBus
from aios_core.memory_manager import MemoryManager
from aios_core.rate_limiter import RateLimiter

def test():
    db = Database(":memory:")
    kg = KnowledgeGraph()
    eb = EventBus()
    mm = MemoryManager()
    rl = RateLimiter()
    assert db.stats() is not None
    assert kg.stats() is not None
    assert rl.is_allowed("t") is True
    mm.store({"x":1},"o")
    eb.on("e",lambda p:None)
    eb.emit("e",{})
    assert mm.stats() is not None
