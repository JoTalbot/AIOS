"""Vector store full."""
from aios_core.vector_store import VectorStore
def test(): s=VectorStore().stats(); assert isinstance(s,dict)
