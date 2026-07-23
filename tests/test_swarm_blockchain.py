"""Tests for swarm, blockchain, and continual learning modules."""

from aios_core.swarm_intelligence import SwarmOptimizer
from aios_core.blockchain import BlockchainLedger
from aios_core.continual_learning import ContinualLearner


def test_swarm_optimizer_stats():
    so = SwarmOptimizer()
    s = so.stats()
    assert isinstance(s, dict)


def test_blockchain_ledger_stats():
    bl = BlockchainLedger()
    s = bl.stats()
    assert isinstance(s, dict)


def test_continual_learner_stats():
    cl = ContinualLearner()
    s = cl.stats()
    assert isinstance(s, dict)
