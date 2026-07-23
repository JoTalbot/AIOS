"""Retry policy operations tests."""
from aios_core.retry import RetryPolicy
def test_retry_defaults():
    rp = RetryPolicy(max_retries=3)
    assert rp.max_retries == 3
