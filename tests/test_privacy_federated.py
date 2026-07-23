"""Tests for privacy, federated learning, and differential privacy."""

from aios_core.federated_learning import FederatedLearning
from aios_core.differential_privacy import DifferentialPrivacy
from aios_core.encryption import EncryptionService


def test_federated_learning_stats():
    fl = FederatedLearning()
    s = fl.stats()
    assert isinstance(s, dict)


def test_differential_privacy_stats():
    dp = DifferentialPrivacy()
    assert dp is not None


def test_encryption_service_stats():
    es = EncryptionService()
    s = es.stats()
    assert isinstance(s, dict)
