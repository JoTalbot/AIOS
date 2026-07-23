"""Parametrized deep 14."""
import pytest
from aios_core.storage import Database
from aios_core.knowledge_graph import KnowledgeGraph
from aios_core.event_bus import EventBus

@pytest.mark.parametrize("n", [1,3,5,10])
def test_kg_14(n):
    kg = KnowledgeGraph()
    for j in range(n): kg.add_node("n"+str(j),dict())
    assert kg.stats() is not None

@pytest.mark.parametrize("n", [1,5,10,50,100])
def test_ev_14(n):
    eb = EventBus()
    r = []
    eb.on("e",lambda p:r.append(p))
    for j in range(n): eb.emit("e",dict())
    assert len(r) == n

@pytest.mark.parametrize("table", ["tasks","plans","events"])
def test_tb_14(table):
    db = Database(":memory:")
    assert db.row_count(table) in (0, None)
