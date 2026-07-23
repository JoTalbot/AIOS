"""test_marketplace_v2 test."""
from aios_core.marketplace import Marketplace
def test(): assert Marketplace().stats() is not None
