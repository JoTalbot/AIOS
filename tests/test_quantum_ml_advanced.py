"""Tests for quantum ML, NLP, vision, and reinforcement modules."""

from aios_core.quantum_ml_advanced import AdvancedQuantumML
from aios_core.quantum_nlp import QuantumNLP
from aios_core.quantum_vision import QuantumVision
from aios_core.quantum_reinforcement import QuantumReinforcement
from aios_core.quantum_advantage import QuantumAdvantage


def test_advanced_quantum_ml_stats():
    s = AdvancedQuantumML().stats()
    assert isinstance(s, dict)


def test_quantum_nlp_stats():
    s = QuantumNLP().stats()
    assert isinstance(s, dict)


def test_quantum_vision_stats():
    s = QuantumVision().stats()
    assert isinstance(s, dict)


def test_quantum_reinforcement_stats():
    s = QuantumReinforcement().stats()
    assert isinstance(s, dict)


def test_quantum_advantage_stats():
    s = QuantumAdvantage().stats()
    assert isinstance(s, dict)
