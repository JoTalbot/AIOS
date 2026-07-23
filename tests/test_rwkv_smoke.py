"""rwkv smoke test."""
def test_rwkv(): from aios_core.rwkv import RWKVModel; assert RWKVModel().stats() is not None
