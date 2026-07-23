"""Topological full ops."""
from aios_core.topological import TopologicalDataAnalysis
def test_tda(): s=TopologicalDataAnalysis().stats(); assert isinstance(s,dict)
