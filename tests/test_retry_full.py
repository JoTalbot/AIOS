"""Retry policy full."""
from aios_core.retry import RetryPolicy
def test(): rp=RetryPolicy(max_retries=5); assert rp.max_retries==5
