from aios_core.edge_computing import EdgeNode
from aios_core.distributed_computing import DistributedRuntime
def test(): assert EdgeNode("n1").stats() is not None; assert EdgeNode("n2").stats() is not None; assert DistributedRuntime().stats() is not None
