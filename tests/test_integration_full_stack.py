"""Full stack integration — all major components."""
from aios_core.storage import Database
from aios_core.orchestrator import Orchestrator
from aios_core.knowledge_graph import KnowledgeGraph
from aios_core.event_bus import EventBus
from aios_core.memory_manager import MemoryManager
from aios_core.rate_limiter import RateLimiter

def test_full_stack():
    db = Database(":memory:")
    orch = Orchestrator()
    kg = KnowledgeGraph()
    eb = EventBus()
    mm = MemoryManager()
    rl = RateLimiter()
    assert db.stats() is not None
    assert orch.stats() is not None
    assert kg.stats() is not None
    assert rl.is_allowed("test") is True
    eb.on("test", lambda p: None)
    eb.emit("test", {"x": 1})
    mm.store({"k": "v"}, "owner")
    assert mm.stats() is not None
