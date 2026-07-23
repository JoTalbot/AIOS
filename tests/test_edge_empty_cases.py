"""Edge case tests — empty/null inputs."""
from aios_core.active_learning import ActiveLearner
from aios_core.benchmark import Benchmark
from aios_core.rate_limiter import RateLimiter

def test_active_learner_query_empty():
    assert ActiveLearner().query() == {}

def test_benchmark_compare_empty():
    assert "Insufficient" in Benchmark().compare("a", "b")

def test_rate_limiter_zero_rpm():
    rl = RateLimiter(requests_per_minute=0)
    assert rl.is_allowed("k") is False
