"""neuromorphic_matrix test."""
def test(): from aios_core.neuromorphic_matrix import NeuromorphicMatrix; s = NeuromorphicMatrix().stats(); assert isinstance(s, dict)
