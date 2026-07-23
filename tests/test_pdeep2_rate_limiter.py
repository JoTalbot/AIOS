"""Parametrized deep: rate_limiter."""
import pytest
from aios_core.rate_limiter import RateLimiter
@pytest.mark.parametrize("rpm",[1,2,5,10,20,50,100,500])
def test_rl(rpm):
    rl = RateLimiter(rpm)
    for _ in range(rpm): assert rl.is_allowed("k")
    assert not rl.is_allowed("k")

