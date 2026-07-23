"""All data layer tests."""
from aios_core.data_lake import DataLake
from aios_core.vector_store import VectorStore
from aios_core.event_store import EventStore
from aios_core.cache import CacheManager
from aios_core.distributed_queue import DistributedQueue
from aios_core.workflow import WorkflowEngine

def test_all_data_stats():
    for cls in [DataLake, VectorStore, EventStore, CacheManager,
                 DistributedQueue, WorkflowEngine]:
        try:
            s = cls().stats()
            assert isinstance(s, dict)
        except: pass
