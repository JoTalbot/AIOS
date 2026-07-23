"""Z-test 2628."""
from aios_core.storage import Database
from aios_core.knowledge_graph import KnowledgeGraph
from aios_core.event_bus import EventBus
from aios_core.rate_limiter import RateLimiter
from aios_core.circuit_breaker import CircuitBreaker
from aios_core.self_healing import SelfHealing

def test():
    db=Database(":memory:")
    kg=KnowledgeGraph()
    eb=EventBus()
    rl=RateLimiter()
    cb=CircuitBreaker()
    sh=SelfHealing()
    assert db.stats() is not None
    kg.add_node("a",dict())
    kg.add_node("b",dict())
    kg.add_edge("a","b","r")
    assert kg.stats() is not None
    assert rl.is_allowed("z") is True
    r=[]
    eb.on("z",lambda p:r.append(p))
    eb.emit("z",{"idx":28})
    assert len(r)==1
    assert sh.stats() is not None
