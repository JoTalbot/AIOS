"""Test federated and privacy."""
from aios_core.federated_learning import FederatedLearning
from aios_core.federated_analytics import FederatedAnalytics
def test_fed(): assert FederatedLearning().stats() is not None
def test_fa(): assert FederatedAnalytics().stats() is not None
