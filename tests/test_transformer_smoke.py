"""transformer smoke test."""
def test_tf(): from aios_core.transformer import TransformerModel; assert TransformerModel().stats() is not None
