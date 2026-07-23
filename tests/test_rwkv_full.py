"""RWKV full ops."""
from aios_core.rwkv import RWKVModel
def test(): s=RWKVModel().stats(); assert isinstance(s,dict)
