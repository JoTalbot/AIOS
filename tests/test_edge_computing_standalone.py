"""Edge computing standalone test."""
from aios_core.edge_computing import EdgeNode
def test_init(): assert EdgeNode("n1").stats() is not None
