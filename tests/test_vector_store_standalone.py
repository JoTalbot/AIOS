"""vector_store standalone test."""
from aios_core.vector_store import VectorStore
def test_init(): s = VectorStore().stats(); assert isinstance(s, dict)
