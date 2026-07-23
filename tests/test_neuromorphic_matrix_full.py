"""Neuromorphic matrix full."""
from aios_core.neuromorphic_matrix import NeuromorphicMatrix
def test(): s=NeuromorphicMatrix().stats(); assert isinstance(s,dict)
