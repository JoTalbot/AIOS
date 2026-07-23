"""topological smoke test."""
def test_tda(): from aios_core.topological import TopologicalDataAnalysis; assert TopologicalDataAnalysis().stats() is not None
