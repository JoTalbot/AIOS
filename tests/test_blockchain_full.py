"""Blockchain full ops."""
from aios_core.blockchain import BlockchainLedger
def test(): s=BlockchainLedger().stats(); assert isinstance(s,dict)
