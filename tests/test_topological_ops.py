from aios_core.topological import TopologicalDataAnalysis
def test_ops():
    tda = TopologicalDataAnalysis()
    assert tda.stats() is not None