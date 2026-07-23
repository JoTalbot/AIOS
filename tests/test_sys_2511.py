"""System test 2511."""
from aios_core.storage import Database
from aios_core.orchestrator import Orchestrator
from aios_core.knowledge_graph import KnowledgeGraph
from aios_core.event_bus import EventBus
from aios_core.rate_limiter import RateLimiter
from aios_core.circuit_breaker import CircuitBreaker

def test():
    db = Database(":memory:")
    o = Orchestrator()
    kg = KnowledgeGraph()
    eb = EventBus()
    rl = RateLimiter()
    cb = CircuitBreaker()
    assert db.stats() is not None
    assert o.stats() is not None
    assert kg.stats() is not None
    kg.add_node("x",{}); kg.add_node("y",{})
    assert kg.add_edge("x","y","r") is not None
    assert rl.is_allowed("k") is True
    r=[]; eb.on("e",lambda p:r.append(p))
    eb.emit("e",{"v":42})
    assert len(r)==1
