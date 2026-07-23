"""Marketplace ops."""
from aios_core.marketplace import Marketplace
def test_market(): m = Marketplace(); assert m.stats() is not None
