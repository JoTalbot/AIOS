"""Tests for platforms sub-modules — resolver, compliance, pacing, promote."""

from aios_core.platforms.resolver import resolve_profile
from aios_core.platforms.compliance import compliance_guard
from aios_core.platforms.pacing import Pacer


def test_pacer_stats():
    p = Pacer(actions_per_hour=30)
    s = p.stats()
    assert isinstance(s, dict)


def test_pacer_allow_first():
    p = Pacer(actions_per_hour=60)
    assert p.allow() is True
