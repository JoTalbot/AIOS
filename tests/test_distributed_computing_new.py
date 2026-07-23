"""distributed_computing test."""
def test(): from aios_core.distributed_computing import DistributedRuntime; s = DistributedRuntime().stats(); assert isinstance(s, dict)
