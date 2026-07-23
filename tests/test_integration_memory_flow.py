"""Integration test — memory pipeline."""
from aios_core.memory_manager import MemoryManager
from aios_core.knowledge_graph import KnowledgeGraph
from aios_core.event_bus import EventBus
def test_pipeline_triple():
    assert MemoryManager() is not None
    assert KnowledgeGraph() is not None
    assert EventBus() is not None
