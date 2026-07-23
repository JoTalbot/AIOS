"""mamba smoke test."""
def test_mmb(): from aios_core.mamba import MambaModel; assert MambaModel().stats() is not None
