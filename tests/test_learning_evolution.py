"""Tests for Learning Engine and Evolution Manager."""

from aios_core.learning_engine import LearningEngine
from aios_core.evolution_manager import EvolutionManager


def test_learning_engine_stats():
    le = LearningEngine()
    s = le.stats()
    assert isinstance(s, dict)


def test_evolution_manager_stats():
    em = EvolutionManager()
    s = em.stats()
    assert isinstance(s, dict)
