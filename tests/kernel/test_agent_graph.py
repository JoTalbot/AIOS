from aios.kernel.agent_graph import AgentGraph


def test_agent_graph_connect():
    graph = AgentGraph()
    graph.add_agent("a", object())
    graph.add_agent("b", object())
    graph.connect("a", "b")
    assert graph.neighbors("a") == ["b"]
