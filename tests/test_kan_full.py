"""KAN full ops."""
from aios_core.kan import KANetwork
def test(): s=KANetwork().stats(); assert isinstance(s,dict)
