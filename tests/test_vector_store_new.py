"""vector_store test."""
def test(): from aios_core.vector_store import VectorStore; s = VectorStore().stats(); assert isinstance(s, dict)
