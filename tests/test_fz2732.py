"""FZ-test 2732."""
from aios_core.storage import Database
from aios_core.knowledge_graph import KnowledgeGraph
from aios_core.event_bus import EventBus
from aios_core.memory_manager import MemoryManager

def test():
    db=Database(":memory:")
    kg=KnowledgeGraph()
    eb=EventBus()
    mm=MemoryManager()
    assert db.stats() is not None
    kg.add_node("x",dict())
    kg.add_node("y",dict())
    kg.add_edge("x","y","link")
    r=[]
    eb.on("f",lambda p:r.append(p))
    eb.emit("f",{"n":32})
    assert len(r)==1
    mm.store({"tag":"test"},"sys")
    assert mm.stats() is not None
