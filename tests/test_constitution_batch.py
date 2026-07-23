"""Tests for Constitution engine and validator."""

from aios_core.constitution_engine import ConstitutionEngine
from aios_core.constitution_validator import ConstitutionValidator


def test_constitution_engine_stats():
    ce = ConstitutionEngine()
    s = ce.stats()
    assert isinstance(s, dict)


def test_constitution_validator_stats():
    cv = ConstitutionValidator()
    s = cv.stats()
    assert isinstance(s, dict)
