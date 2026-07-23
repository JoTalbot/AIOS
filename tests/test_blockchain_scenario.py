"""test_blockchain_scenario test."""
from aios_core.blockchain import BlockchainLedger
from aios_core.swarm_intelligence import SwarmOptimizer

def test_decentralized():
    assert BlockchainLedger().stats() is not None
    assert SwarmOptimizer().stats() is not None

