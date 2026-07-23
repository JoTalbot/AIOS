"""RetNet full ops."""
from aios_core.retnet import RetNet
def test(): s=RetNet().stats(); assert isinstance(s,dict)
