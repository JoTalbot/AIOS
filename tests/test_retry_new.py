"""retry test."""
def test(): from aios_core.retry import RetryPolicy; rp = RetryPolicy(max_retries=5); assert rp.max_retries == 5
