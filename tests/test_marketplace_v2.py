"""test_marketplace_v2 test."""
from aios_core.marketplace import CapabilityMarketplace
def test(): assert CapabilityMarketplace().stats() is not None
