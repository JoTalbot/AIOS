"""Distributed compute full."""
from aios_core.distributed_computing import DistributedRuntime
def test(): s=DistributedRuntime().stats(); assert isinstance(s,dict)
