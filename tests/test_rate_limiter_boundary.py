"""rate_limiter boundary test."""
from aios_core.rate_limiter import RateLimiter

def test_default_allows(): assert RateLimiter().is_allowed('k') is True
