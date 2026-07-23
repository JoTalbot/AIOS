"""W-test 3097."""
from aios_core.data_lake import DataLake
from aios_core.vector_store import VectorStore
from aios_core.event_store import EventStore
from aios_core.distributed_queue import DistributedQueue
from aios_core.workflow import WorkflowEngine
from aios_core.cache import CacheManager
from aios_core.blockchain import BlockchainLedger

def test():
    for o in [DataLake(),VectorStore(),EventStore(),DistributedQueue(),WorkflowEngine(),CacheManager(),BlockchainLedger()]:
        s = o.stats()
        assert s is not None
