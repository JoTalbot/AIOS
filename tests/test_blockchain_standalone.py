"""blockchain standalone test."""
from aios_core.blockchain import BlockchainLedger
def test_init(): s = BlockchainLedger().stats(); assert isinstance(s, dict)
