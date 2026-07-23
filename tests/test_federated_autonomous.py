"""Tests for federation, autonomous evolution, and federated analytics."""

from aios_core.autonomous_evolution import AutonomousEvolution
from aios_core.federated_analytics import FederatedAnalytics
from aios_core.continuous_learning import ContinuousLearner
from aios_core.neural_ode import NeuralODE


def test_autonomous_evolution_stats():
    s = AutonomousEvolution().stats()
    assert isinstance(s, dict)


def test_federated_analytics_stats():
    s = FederatedAnalytics().stats()
    assert isinstance(s, dict)


def test_continuous_learner_stats():
    s = ContinuousLearner().stats()
    assert isinstance(s, dict)


def test_neural_ode_stats():
    s = NeuralODE().stats()
    assert isinstance(s, dict)
