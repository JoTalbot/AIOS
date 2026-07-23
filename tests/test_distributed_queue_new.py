"""distributed_queue test."""
def test(): from aios_core.distributed_queue import DistributedQueue; s = DistributedQueue().stats(); assert isinstance(s, dict)
