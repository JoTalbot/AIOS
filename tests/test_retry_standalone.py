"""retry test."""
from aios_core.retry import RetryPolicy
def test_init(): assert RetryPolicy(max_retries=3).max_retries == 3
