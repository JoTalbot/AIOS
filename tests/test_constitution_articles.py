"""Tests for constitution article loader and policy engine."""

from aios_core.constitution_loader import ConstitutionLoader
from aios_core.policy_loader import PolicyLoader
from aios_core.runtime_policy import RuntimePolicy


def test_constitution_loader_stats():
    cl = ConstitutionLoader()
    s = cl.stats()
    assert isinstance(s, dict)


def test_policy_loader_init():
    pl = PolicyLoader()
    assert pl is not None


def test_runtime_policy_init():
    rp = RuntimePolicy()
    assert rp is not None
