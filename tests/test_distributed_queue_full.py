"""Distributed queue full."""
from aios_core.distributed_queue import DistributedQueue
def test(): s=DistributedQueue().stats(); assert isinstance(s,dict)
