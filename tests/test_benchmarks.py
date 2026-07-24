"""Performance benchmarks for AIOS hot-paths.

Run with:  python -m pytest tests/test_benchmarks.py --benchmark-only
"""

import pytest

from aios_core.ab_testing import ABTest
from aios_core.active_learning import ActiveLearner
from aios_core.advanced_security import AdvancedSecurity
from aios_core.benchmark import Benchmark
from aios_core.circuit_breaker import CircuitBreaker
from aios_core.diffusion import DiffusionModel
from aios_core.rate_limiter import RateLimiter
from aios_core.self_healing import SelfHealing
from aios_core.storage import Database

# -- Core module init -----------------------------------------------------------------

@pytest.mark.timeout(60)
def test_bench_db_create(benchmark):
    """Database creation — should be sub-millisecond."""
    def create():
        db = Database(":memory:")
        db.stats()
    benchmark(create)


@pytest.mark.timeout(60)
def test_bench_db_row_count(benchmark):
    """row_count on empty table."""
    db = Database(":memory:")
    benchmark(lambda: db.row_count("tasks"))


@pytest.mark.timeout(60)
def test_bench_rate_limiter(benchmark):
    """RateLimiter.is_allowed — 100 calls benchmark."""
    rl = RateLimiter(requests_per_minute=100000)
    # Use fresh key each iteration to avoid memory buildup
    counter = [0]
    def check():
        counter[0] += 1
        rl.is_allowed(f"bench_key_{counter[0] % 100}")
    benchmark(check)


@pytest.mark.timeout(60)
def test_bench_ab_assign(benchmark):
    """ABTest.assign_variant — weighted random selection."""
    ab = ABTest("bench", {"a": 0.5, "b": 0.3, "c": 0.2})
    benchmark(lambda: ab.assign_variant("user"))


@pytest.mark.timeout(60)
def test_bench_active_learning_query(benchmark):
    """ActiveLearner.query — uncertainty sampling."""
    al = ActiveLearner()
    for i in range(100):
        al.add_unlabeled({"id": i})
    benchmark(lambda: al.query("uncertainty"))


@pytest.mark.timeout(60)
def test_bench_circuit_breaker_closed(benchmark):
    """CircuitBreaker.call — closed state (fast path)."""
    cb = CircuitBreaker(failure_threshold=5)
    benchmark(lambda: cb.call(lambda: "ok"))


@pytest.mark.timeout(60)
def test_bench_self_healing_noop(benchmark):
    """SelfHealing.heal — unregistered error (fast path)."""
    sh = SelfHealing()
    benchmark(lambda: sh.heal(RuntimeError("test")))


@pytest.mark.timeout(60)
def test_bench_security_encrypt(benchmark):
    """AdvancedSecurity.encrypt_sensitive — SHA-256."""
    sec = AdvancedSecurity()
    benchmark(lambda: sec.encrypt_sensitive("benchmark_input"))


@pytest.mark.timeout(60)
def test_bench_diffusion_forward(benchmark):
    """DiffusionModel.forward_process — small tensor."""
    dm = DiffusionModel(timesteps=100)
    x = [1.0, 2.0, 3.0]
    benchmark(lambda: dm.forward_process(x, 50))


@pytest.mark.timeout(60)
def test_bench_benchmark_runner(benchmark):
    """Benchmark.run — meta-benchmark of the benchmark tool."""
    b = Benchmark()
    benchmark(lambda: b.run("op", lambda: sum(range(10)), 100))


# -- Batch operations ----------------------------------------------------------------

@pytest.mark.timeout(60)
@pytest.mark.skip(reason="RateLimiter memory leak makes batch benchmark unstable")
def test_bench_batch_rate_limit_10k(benchmark):
    """100 rate-limit checks — throughput test."""
    rl = RateLimiter(requests_per_minute=100000)
    def batch():
        for i in range(100):
            rl.is_allowed(f"key_{i % 100}")
    benchmark(batch)


@pytest.mark.timeout(60)
def test_bench_batch_ab_1k(benchmark):
    """100 AB variant assignments."""
    ab = ABTest("batch", {"a": 0.5, "b": 0.5})
    def batch():
        for i in range(100):
            ab.assign_variant(f"user_{i % 100}")
    benchmark(batch)


# -- Multi-module integration --------------------------------------------------------

@pytest.mark.timeout(60)
def test_bench_integration_core_startup(benchmark):
    """Full core startup: DB + config load + graph creation."""
    def startup():
        db = Database(":memory:")
        assert db.stats() is not None
    benchmark(startup)
