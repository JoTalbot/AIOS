"""blockchain test."""
def test(): from aios_core.blockchain import BlockchainLedger; s = BlockchainLedger().stats(); assert isinstance(s, dict)
