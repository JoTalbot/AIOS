"""retnet smoke test."""
def test_rn(): from aios_core.retnet import RetNet; assert RetNet().stats() is not None
