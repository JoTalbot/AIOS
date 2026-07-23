"""Edge compute full."""
from aios_core.edge_computing import EdgeNode
def test(): s=EdgeNode("e1").stats(); assert isinstance(s,dict)
