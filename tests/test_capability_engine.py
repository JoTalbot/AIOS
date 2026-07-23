"""Tests for capability engine."""

from aios_core.capability_engine import CapabilityEngine


def test_capability_engine_init():
    ce = CapabilityEngine()
    assert ce is not None


def test_capability_engine_stats():
    ce = CapabilityEngine()
    s = ce.stats()
    assert isinstance(s, dict)
