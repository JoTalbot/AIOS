"""V-test 2814."""
from aios_core.storage import Database
from aios_core.knowledge_graph import KnowledgeGraph
from aios_core.event_bus import EventBus
from aios_core.rate_limiter import RateLimiter
from aios_core.circuit_breaker import CircuitBreaker
from aios_core.self_healing import SelfHealing
from aios_core.memory_manager import MemoryManager

def test():
    db=Database(":memory:")
    kg=KnowledgeGraph()
    eb=EventBus()
    rl=RateLimiter()
    cb=CircuitBreaker()
    sh=SelfHealing()
    mm=MemoryManager()
    assert db.stats() is not None
    kg.add_node("a",dict())
    kg.add_node("b",dict())
    kg.add_edge("a","b","link")
    assert kg.stats() is not None
    assert rl.is_allowed("t") is True
    r=[]
    eb.on("ev",lambda p:r.append(p))
    eb.emit("ev",{"k":"v"})
    assert len(r)==1
    mm.store({"data":"test"},"owner")
    assert mm.stats() is not None
    assert sh.stats() is not None
    assert cb.state is not None
