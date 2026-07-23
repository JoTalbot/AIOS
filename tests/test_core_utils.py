"""Tests for core utility modules."""

from aios_core.retry import RetryPolicy
from aios_core.cache import CacheManager
from aios_core.health_checks import HealthChecker
from aios_core.graceful_shutdown import GracefulShutdown


def test_retry_policy_defaults():
    rp = RetryPolicy()
    assert rp is not None


def test_cache_manager_init():
    cm = CacheManager()
    assert cm is not None


def test_health_checker_init():
    hc = HealthChecker()
    assert hc is not None


def test_graceful_shutdown_init():
    gs = GracefulShutdown()
    assert gs is not None
