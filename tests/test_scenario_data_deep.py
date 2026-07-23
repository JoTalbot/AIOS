"""Data layer deep scenario."""
from aios_core.data_lake import DataLake
from aios_core.vector_store import VectorStore
from aios_core.event_store import EventStore
from aios_core.distributed_queue import DistributedQueue
from aios_core.workflow import WorkflowEngine
from aios_core.cache import CacheManager

def test_data_stack():
    for obj in [DataLake(), VectorStore(), EventStore(),
                DistributedQueue(), WorkflowEngine(), CacheManager()]:
        s = obj.stats()
        assert isinstance(s, dict)
