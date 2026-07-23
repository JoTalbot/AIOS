"""Tests for category theory, topological, and uncertainty modules."""

from aios_core.category_theory import CategoryTheory
from aios_core.topological import TopologicalDataAnalysis
from aios_core.uncertainty import UncertaintyQuantifier
from aios_core.type_theory import TypeTheoryChecker


def test_category_theory_stats():
    s = CategoryTheory().stats()
    assert isinstance(s, dict)


def test_topological_stats():
    s = TopologicalDataAnalysis().stats()
    assert isinstance(s, dict)


def test_uncertainty_stats():
    s = UncertaintyQuantifier().stats()
    assert isinstance(s, dict)


def test_type_theory_stats():
    s = TypeTheoryChecker().stats()
    assert isinstance(s, dict)
