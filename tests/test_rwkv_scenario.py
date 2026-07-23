"""test_rwkv_scenario test."""
from aios_core.rwkv import RWKVModel

def test_rwkv():
    s = RWKVModel().stats()
    assert isinstance(s, dict)

