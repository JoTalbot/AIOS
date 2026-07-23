"""graph_transformer smoke test."""
def test_gt(): from aios_core.graph_transformer import GraphTransformer; assert GraphTransformer().stats() is not None
