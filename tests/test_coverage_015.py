"""Test sparse autoencoder."""
from aios_core.ai_safety_sparse_autoencoder import SparseAutoencoder
def test_sparse(): assert SparseAutoencoder().stats() is not None
