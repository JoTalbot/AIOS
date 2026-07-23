"""Marketplace full ops."""
from aios_core.marketplace import Marketplace
def test_search(): m=Marketplace(); r=m.search("test"); assert isinstance(r,list)
