"""Infinite constitution full."""
from aios_core.infinite_constitution import InfiniteConstitution
def test(): s=InfiniteConstitution().stats(); assert isinstance(s,dict)
