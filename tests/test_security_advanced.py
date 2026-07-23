"""Tests for advanced security — RBAC, retry, multitenancy, observability."""

from aios_core.rbac import RBACManager
from aios_core.retry import RetryPolicy
from aios_core.multitenancy import TenantManager


def test_rbac_manager_stats():
    rm = RBACManager()
    s = rm.stats()
    assert isinstance(s, dict)


def test_retry_policy_stats():
    rp = RetryPolicy(max_retries=3)
    assert rp.max_retries == 3


def test_tenant_manager_stats():
    tm = TenantManager()
    s = tm.stats()
    assert isinstance(s, dict)
