"""Biological evolution full."""
from aios_core.biological_evolution import BiologicalEvolution
def test(): s=BiologicalEvolution().stats(); assert isinstance(s,dict)
