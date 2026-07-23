"""Integration3 2435."""
from aios_core.storage import Database
from aios_core.knowledge_graph import KnowledgeGraph
from aios_core.event_bus import EventBus
from aios_core.rate_limiter import RateLimiter
from aios_core.circuit_breaker import CircuitBreaker

def test():
    db = Database(":memory:")
    kg = KnowledgeGraph()
    eb = EventBus()
    rl = RateLimiter()
    cb = CircuitBreaker()
    assert db.stats() is not None
    kg.add_node("a",{}); kg.add_node("b",{})
    kg.add_edge("a","b","r")
    assert kg.stats() is not None
    assert rl.is_allowed("k") is True
    r=[]; eb.on("e",lambda p:r.append(p))
    eb.emit("e",{"x":1})
    assert len(r)==1
