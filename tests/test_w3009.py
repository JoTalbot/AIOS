"""W-test 3009."""
from aios_core.storage import Database
from aios_core.knowledge_graph import KnowledgeGraph
from aios_core.event_bus import EventBus
from aios_core.memory_manager import MemoryManager
from aios_core.rate_limiter import RateLimiter
from aios_core.circuit_breaker import CircuitBreaker
from aios_core.self_healing import SelfHealing
from aios_core.benchmark import Benchmark

def test():
    db=Database(":memory:")
    kg=KnowledgeGraph()
    eb=EventBus()
    mm=MemoryManager()
    rl=RateLimiter()
    cb=CircuitBreaker()
    sh=SelfHealing()
    bm=Benchmark()
    assert db.stats() is not None
    kg.add_node("a",dict());kg.add_node("b",dict())
    kg.add_edge("a","b","r")
    assert kg.stats() is not None
    assert rl.is_allowed("x") is True
    r=[];eb.on("e",lambda p:r.append(p))
    eb.emit("e",dict())
    assert len(r)==1
    mm.store({"k":"v"},"o")
    assert mm.stats() is not None
    assert sh.stats() is not None
    assert cb.state is not None
    assert bm.stats() is not None
