"""distributed_queue standalone test."""
from aios_core.distributed_queue import DistributedQueue
def test_init(): s = DistributedQueue().stats(); assert isinstance(s, dict)
