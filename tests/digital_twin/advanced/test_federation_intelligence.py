from aios.digital_twin.federation_intelligence import TwinStateExchange
from aios.digital_twin.knowledge_graph import KnowledgeGraph
from aios.digital_twin.predictive_routing import rank_nodes


def test_state_exchange():
    exchange = TwinStateExchange()
    exchange.publish("node-b", {"load": 2})
    exchange.publish("node-a", {"load": 1})
    assert exchange.active_nodes() == ["node-a", "node-b"]
    assert exchange.snapshot()["node-a"]["load"] == 1


def test_knowledge_graph():
    graph = KnowledgeGraph()
    graph.add_node("a")
    graph.add_node("b")
    graph.add_edge("a", "depends_on", "b")
    assert graph.edges == [("a", "depends_on", "b")]


def test_predictive_routing():
    assert rank_nodes({"a": 0.8, "b": 0.2}, ["a", "b"]) == ["b", "a"]
