"""Graph transformer full."""
from aios_core.graph_transformer import GraphTransformer
def test_gt(): s=GraphTransformer().stats(); assert isinstance(s,dict)
