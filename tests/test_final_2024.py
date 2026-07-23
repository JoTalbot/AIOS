"""Final batch test."""
from aios_core.storage import Database
from aios_core.orchestrator import Orchestrator
from aios_core.knowledge_graph import KnowledgeGraph

def test():
    assert Database(":memory:").stats() is not None
    assert Orchestrator().stats() is not None
    assert KnowledgeGraph().stats() is not None
